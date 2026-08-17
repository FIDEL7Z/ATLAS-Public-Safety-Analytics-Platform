-- ATLAS — Fase 3 — Views de apoio à página 06 (Data Quality) do dashboard.
--
-- A página de Data Quality precisa mostrar, entre outras coisas, quantos
-- valores "não informados" existem por indicador (Fase 1, seção 9 do
-- DATA_QUALITY_REPORT.md). Essa contagem foi calculada em Python durante o
-- ETL (fact.compute_nao_informado_stats) mas nunca foi persistida em SQL —
-- reimplementada aqui em SQL puro para que o Power BI possa importá-la
-- diretamente, sem depender de um relatório Markdown estático.

DROP VIEW IF EXISTS analytics.vw_qualidade_nao_informado CASCADE;
CREATE VIEW analytics.vw_qualidade_nao_informado AS
WITH grao_real AS (
    -- mesma agregação pelo grão real da Fase 1 (src/transformation/fact.py),
    -- reconstruída a partir de stg_sinesp para obter o denominador correto
    -- ("quantas combinações de grão existem", aplicável ou não).
    SELECT
        evento, uf, municipio, data_referencia, abrangencia, agente, arma, faixa_etaria,
        SUM(feminino) AS feminino, SUM(masculino) AS masculino, SUM(nao_informado) AS nao_informado,
        SUM(total) AS total, SUM(total_peso) AS total_peso
    FROM stg_sinesp
    GROUP BY evento, uf, municipio, data_referencia, abrangencia, agente, arma, faixa_etaria
),
por_evento AS (
    SELECT
        g.evento, di.familia_medida,
        COUNT(*) AS linhas_grao_real,
        CASE di.familia_medida
            WHEN 'vitima' THEN COUNT(*) * 3
            ELSE COUNT(*)
        END AS valores_aplicaveis,
        CASE di.familia_medida
            WHEN 'vitima' THEN
                COUNT(*) FILTER (WHERE g.feminino IS NULL)
                + COUNT(*) FILTER (WHERE g.masculino IS NULL)
                + COUNT(*) FILTER (WHERE g.nao_informado IS NULL)
            WHEN 'contagem' THEN COUNT(*) FILTER (WHERE g.total IS NULL)
            WHEN 'peso' THEN COUNT(*) FILTER (WHERE g.total_peso IS NULL)
        END AS valores_nao_informados
    FROM grao_real g
    JOIN dim_indicador di ON di.evento = g.evento
    GROUP BY g.evento, di.familia_medida
)
SELECT
    evento, familia_medida, linhas_grao_real, valores_aplicaveis, valores_nao_informados,
    ROUND(100.0 * valores_nao_informados / NULLIF(valores_aplicaveis, 0), 2) AS pct_nao_informado
FROM por_evento;

COMMENT ON VIEW analytics.vw_qualidade_nao_informado IS
'Réplica em SQL do cálculo feito em Python na Fase 1 (fact.compute_nao_informado_stats) — mesmos números, agora consultável/importável diretamente. Ver teste de paridade em tests/test_analytics_sql.py.';

-- Resumo executivo de cobertura/qualidade — alimenta os KPI cards da página
-- de Data Quality (uma linha só, fácil de usar como "card" no Power BI).
DROP VIEW IF EXISTS analytics.vw_qualidade_resumo CASCADE;
CREATE VIEW analytics.vw_qualidade_resumo AS
SELECT
    (SELECT COUNT(*) FROM stg_sinesp) AS linhas_raw_staging,
    (SELECT COUNT(*) FROM fact_indicadores) AS linhas_fact,
    (SELECT COUNT(DISTINCT evento) FROM dim_indicador) AS n_indicadores,
    (SELECT COUNT(DISTINCT uf) FROM dim_localidade) AS n_ufs,
    (SELECT COUNT(DISTINCT municipio) FROM dim_localidade) AS n_municipios_distintos,
    (SELECT COUNT(*) FROM dim_localidade) AS n_combinacoes_uf_municipio,
    (SELECT MIN(data_referencia) FROM dim_tempo) AS periodo_inicio,
    (SELECT MAX(data_referencia) FROM dim_tempo) AS periodo_fim,
    (SELECT COUNT(*) FROM dim_tempo WHERE is_partial_year) AS meses_em_anos_parciais,
    (SELECT COUNT(DISTINCT ano) FROM dim_tempo WHERE is_partial_year) AS anos_parciais,
    (SELECT ROUND(AVG(pct_nao_informado), 2) FROM analytics.vw_qualidade_nao_informado) AS pct_nao_informado_medio;

COMMENT ON VIEW analytics.vw_qualidade_resumo IS
'Uma linha com os números-chave de cobertura/qualidade para os KPI cards da página Data Quality do dashboard.';
