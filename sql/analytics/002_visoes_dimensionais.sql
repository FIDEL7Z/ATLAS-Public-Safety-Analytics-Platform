-- ATLAS — Fase 2 — Views dimensionais (01, 03-10 do escopo da Fase 2).
--
-- ESTRATÉGIA DE PERFORMANCE (ver docs/ANALYTICS_MODEL.md, seção Performance):
-- as views que tocam a fact_indicadores inteira (01, 03, 04, 05, 06) agregam
-- PRIMEIRO em chaves inteiras direto sobre fact_indicadores (sem juntar as
-- tabelas de dimensão largas antes de agregar) e só then juntam os rótulos
-- (evento, uf, município...) sobre o resultado já pequeno. Medido via
-- EXPLAIN ANALYZE: agregar-depois-juntar (o que a view
-- analytics.vw_fato_enriquecido faria se usada ingenuamente aqui) levava
-- ~13s para vw_nacional; agregar-antes-de-juntar leva <1s. As views 07-10
-- (sexo/faixa/agente/arma) já filtram um subconjunto pequeno da fact table e
-- não precisaram da mesma reestruturação.

-- Views internas de agregação (prefixo `_agg_`): não são catálogo público de
-- consumo do Power BI, existem só para não repetir a agregação pesada em
-- cada view dimensional que precisa dela.

DROP VIEW IF EXISTS analytics._agg_indicador_ano CASCADE;
CREATE VIEW analytics._agg_indicador_ano AS
SELECT
    indicador_id, ano_origem AS ano,
    COUNT(*) AS n_registros,
    SUM(valor) AS total,
    AVG(valor) AS media,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor) AS mediana,
    MIN(valor) AS minimo,
    MAX(valor) AS maximo,
    STDDEV_POP(valor) AS desvio_padrao
FROM fact_indicadores
GROUP BY indicador_id, ano_origem;

DROP VIEW IF EXISTS analytics._agg_indicador_localidade_ano CASCADE;
CREATE VIEW analytics._agg_indicador_localidade_ano AS
SELECT indicador_id, localidade_id, ano_origem AS ano, SUM(valor) AS total
FROM fact_indicadores
GROUP BY indicador_id, localidade_id, ano_origem;

DROP VIEW IF EXISTS analytics._agg_indicador_abrangencia_ano CASCADE;
CREATE VIEW analytics._agg_indicador_abrangencia_ano AS
SELECT indicador_id, abrangencia_id, ano_origem AS ano, SUM(valor) AS total, COUNT(*) AS n_registros
FROM fact_indicadores
GROUP BY indicador_id, abrangencia_id, ano_origem;

-- ano -> is_partial_year (tabela pequena, 1 linha por ano, usada como lookup
-- leve em vez de juntar dim_tempo inteira, que é por mês)
DROP VIEW IF EXISTS analytics._dim_ano CASCADE;
CREATE VIEW analytics._dim_ano AS
SELECT DISTINCT ano, is_partial_year FROM dim_tempo;

-- 01 — VISÃO NACIONAL: um indicador, um ano, os números-chave.
DROP VIEW IF EXISTS analytics.vw_nacional CASCADE;
CREATE VIEW analytics.vw_nacional AS
SELECT
    i.evento, i.familia_medida, i.unidade, i.tipo_indicador,
    CASE
        WHEN i.tipo_indicador LIKE 'Vítima%' OR i.tipo_indicador LIKE 'Pessoa%' THEN 'Vítimas'
        WHEN i.tipo_indicador = 'Ação Policial' THEN 'Ações Policiais'
        WHEN i.tipo_indicador LIKE 'Ocorrência%' THEN 'Ocorrências'
        WHEN i.tipo_indicador = 'Apreensão - Peso' THEN 'Apreensões (Peso)'
        WHEN i.tipo_indicador = 'Apreensão - Unidade' THEN 'Apreensões (Unidade)'
        WHEN i.tipo_indicador LIKE 'Serviço%' THEN 'Serviços'
        ELSE 'Outro'
    END AS grupo_semantico,
    a.ano, ap.is_partial_year,
    a.n_registros, a.total, a.media, a.mediana, a.minimo, a.maximo, a.desvio_padrao
FROM analytics._agg_indicador_ano a
JOIN dim_indicador i ON a.indicador_id = i.indicador_id
JOIN analytics._dim_ano ap ON a.ano = ap.ano;

COMMENT ON VIEW analytics.vw_nacional IS '01 — Visão nacional: total/média/mediana/min/max por indicador e ano.';

-- 03 — ANÁLISE POR UF
DROP VIEW IF EXISTS analytics.vw_uf CASCADE;
CREATE VIEW analytics.vw_uf AS
SELECT
    i.evento, i.familia_medida, i.unidade,
    CASE
        WHEN i.tipo_indicador LIKE 'Vítima%' OR i.tipo_indicador LIKE 'Pessoa%' THEN 'Vítimas'
        WHEN i.tipo_indicador = 'Ação Policial' THEN 'Ações Policiais'
        WHEN i.tipo_indicador LIKE 'Ocorrência%' THEN 'Ocorrências'
        WHEN i.tipo_indicador = 'Apreensão - Peso' THEN 'Apreensões (Peso)'
        WHEN i.tipo_indicador = 'Apreensão - Unidade' THEN 'Apreensões (Unidade)'
        WHEN i.tipo_indicador LIKE 'Serviço%' THEN 'Serviços'
        ELSE 'Outro'
    END AS grupo_semantico,
    l.uf, l.regiao, a.ano, ap.is_partial_year,
    SUM(a.total) AS total,
    AVG(a.total) AS media
FROM analytics._agg_indicador_localidade_ano a
JOIN dim_indicador i ON a.indicador_id = i.indicador_id
JOIN dim_localidade l ON a.localidade_id = l.localidade_id
JOIN analytics._dim_ano ap ON a.ano = ap.ano
GROUP BY i.evento, i.familia_medida, i.unidade, i.tipo_indicador, l.uf, l.regiao, a.ano, ap.is_partial_year;

COMMENT ON VIEW analytics.vw_uf IS '03 — Totais e médias por UF/Região, por indicador e ano.';

-- 04 — ANÁLISE POR MUNICÍPIO
DROP VIEW IF EXISTS analytics.vw_municipio CASCADE;
CREATE VIEW analytics.vw_municipio AS
SELECT
    i.evento, i.familia_medida, i.unidade,
    CASE
        WHEN i.tipo_indicador LIKE 'Vítima%' OR i.tipo_indicador LIKE 'Pessoa%' THEN 'Vítimas'
        WHEN i.tipo_indicador = 'Ação Policial' THEN 'Ações Policiais'
        WHEN i.tipo_indicador LIKE 'Ocorrência%' THEN 'Ocorrências'
        WHEN i.tipo_indicador = 'Apreensão - Peso' THEN 'Apreensões (Peso)'
        WHEN i.tipo_indicador = 'Apreensão - Unidade' THEN 'Apreensões (Unidade)'
        WHEN i.tipo_indicador LIKE 'Serviço%' THEN 'Serviços'
        ELSE 'Outro'
    END AS grupo_semantico,
    l.uf, l.municipio, a.ano, ap.is_partial_year,
    a.total
FROM analytics._agg_indicador_localidade_ano a
JOIN dim_indicador i ON a.indicador_id = i.indicador_id
JOIN dim_localidade l ON a.localidade_id = l.localidade_id
JOIN analytics._dim_ano ap ON a.ano = ap.ano;

COMMENT ON VIEW analytics.vw_municipio IS '04 — Totais por município, por indicador e ano.';

-- 05 — ANÁLISE POR INDICADOR (com participação dentro da própria família)
DROP VIEW IF EXISTS analytics.vw_indicador CASCADE;
CREATE VIEW analytics.vw_indicador AS
SELECT
    i.evento, i.familia_medida, i.unidade, i.tipo_indicador,
    CASE
        WHEN i.tipo_indicador LIKE 'Vítima%' OR i.tipo_indicador LIKE 'Pessoa%' THEN 'Vítimas'
        WHEN i.tipo_indicador = 'Ação Policial' THEN 'Ações Policiais'
        WHEN i.tipo_indicador LIKE 'Ocorrência%' THEN 'Ocorrências'
        WHEN i.tipo_indicador = 'Apreensão - Peso' THEN 'Apreensões (Peso)'
        WHEN i.tipo_indicador = 'Apreensão - Unidade' THEN 'Apreensões (Unidade)'
        WHEN i.tipo_indicador LIKE 'Serviço%' THEN 'Serviços'
        ELSE 'Outro'
    END AS grupo_semantico,
    a.ano,
    a.total, a.media, a.mediana,
    SUM(a.total) OVER (PARTITION BY i.familia_medida, a.ano) AS total_familia_ano,
    ROUND(100.0 * a.total / NULLIF(SUM(a.total) OVER (PARTITION BY i.familia_medida, a.ano), 0), 2) AS participacao_pct_na_familia
FROM analytics._agg_indicador_ano a
JOIN dim_indicador i ON a.indicador_id = i.indicador_id;

COMMENT ON VIEW analytics.vw_indicador IS
'05 — Totais por indicador/ano com participação percentual DENTRO da própria familia_medida (nunca contra o total geral, que misturaria unidades).';

-- 06 — ANÁLISE POR ABRANGÊNCIA
DROP VIEW IF EXISTS analytics.vw_abrangencia CASCADE;
CREATE VIEW analytics.vw_abrangencia AS
SELECT
    i.evento, i.familia_medida, i.unidade,
    ab.abrangencia, a.ano,
    a.total, a.n_registros
FROM analytics._agg_indicador_abrangencia_ano a
JOIN dim_indicador i ON a.indicador_id = i.indicador_id
JOIN dim_abrangencia ab ON a.abrangencia_id = ab.abrangencia_id;

COMMENT ON VIEW analytics.vw_abrangencia IS '06 — Totais por abrangência (Estadual/PF/PRF), por indicador e ano.';

-- 07 — ANÁLISE DE SEXO (só existe para a familia_medida = vitima)
DROP VIEW IF EXISTS analytics.vw_sexo CASCADE;
CREATE VIEW analytics.vw_sexo AS
WITH agg AS (
    SELECT indicador_id, sexo_id, ano_origem AS ano, SUM(valor) AS total
    FROM fact_indicadores
    WHERE sexo_id IS NOT NULL
    GROUP BY indicador_id, sexo_id, ano_origem
)
SELECT
    i.evento, i.tipo_indicador, a.ano, s.sexo, a.total,
    ROUND(100.0 * a.total / NULLIF(SUM(a.total) OVER (PARTITION BY a.indicador_id, a.ano), 0), 2) AS participacao_pct
FROM agg a
JOIN dim_indicador i ON a.indicador_id = i.indicador_id
JOIN dim_sexo s ON a.sexo_id = s.sexo_id;

COMMENT ON VIEW analytics.vw_sexo IS
'07 — Distribuição por sexo (Feminino/Masculino/Não Informado) dentro de cada indicador da família vítima. participacao_pct soma 100% por (evento, ano) — total_vitima nunca é armazenado, é sempre SUM(total) desta view sem filtro de sexo.';

-- 08 — ANÁLISE DE FAIXA ETÁRIA (só Pessoa Desaparecida / Pessoa Localizada)
DROP VIEW IF EXISTS analytics.vw_faixa_etaria CASCADE;
CREATE VIEW analytics.vw_faixa_etaria AS
WITH agg AS (
    SELECT indicador_id, faixa_etaria_id, ano_origem AS ano, SUM(valor) AS total
    FROM fact_indicadores
    WHERE faixa_etaria_id IS NOT NULL
    GROUP BY indicador_id, faixa_etaria_id, ano_origem
)
SELECT
    i.evento, a.ano, fe.faixa_etaria, a.total,
    ROUND(100.0 * a.total / NULLIF(SUM(a.total) OVER (PARTITION BY a.indicador_id, a.ano), 0), 2) AS participacao_pct
FROM agg a
JOIN dim_indicador i ON a.indicador_id = i.indicador_id
JOIN dim_faixa_etaria fe ON a.faixa_etaria_id = fe.faixa_etaria_id;

COMMENT ON VIEW analytics.vw_faixa_etaria IS '08 — Distribuição por faixa etária, aplicável apenas a Pessoa Desaparecida/Localizada.';

-- 09 — ANÁLISE DE AGENTE (só Morte/Suicídio de Agente do Estado)
DROP VIEW IF EXISTS analytics.vw_agente CASCADE;
CREATE VIEW analytics.vw_agente AS
WITH agg AS (
    SELECT indicador_id, agente_id, ano_origem AS ano, SUM(valor) AS total
    FROM fact_indicadores
    WHERE agente_id IS NOT NULL
    GROUP BY indicador_id, agente_id, ano_origem
)
SELECT i.evento, a.ano, ag.agente, a.total
FROM agg a
JOIN dim_indicador i ON a.indicador_id = i.indicador_id
JOIN dim_agente ag ON a.agente_id = ag.agente_id;

COMMENT ON VIEW analytics.vw_agente IS '09 — Totais por tipo de agente do Estado, aplicável apenas a Morte/Suicídio de Agente do Estado.';

-- 10 — ANÁLISE DE ARMA (só Arma de Fogo Apreendida)
DROP VIEW IF EXISTS analytics.vw_arma CASCADE;
CREATE VIEW analytics.vw_arma AS
WITH agg AS (
    SELECT arma_id, ano_origem AS ano, SUM(valor) AS total
    FROM fact_indicadores
    WHERE arma_id IS NOT NULL
    GROUP BY arma_id, ano_origem
)
SELECT
    a.ano, ar.arma, a.total,
    RANK() OVER (PARTITION BY a.ano ORDER BY a.total DESC) AS ranking
FROM agg a
JOIN dim_arma ar ON a.arma_id = ar.arma_id;

COMMENT ON VIEW analytics.vw_arma IS '10 — Ranking de tipos de arma apreendida (unidade: armas), por ano.';
