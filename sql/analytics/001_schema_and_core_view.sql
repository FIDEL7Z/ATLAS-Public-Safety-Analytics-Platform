-- ATLAS — Public Safety Analytics Platform
-- Fase 2: camada semântica central. Toda view analítica é construída sobre
-- analytics.vw_fato_enriquecido — nunca diretamente sobre fact_indicadores —
-- para garantir que familia_medida/unidade/grupo_semantico estejam sempre
-- disponíveis e nenhuma agregação possa "esquecer" de filtrar por família.

CREATE SCHEMA IF NOT EXISTS analytics;

DROP VIEW IF EXISTS analytics.vw_fato_enriquecido CASCADE;

CREATE VIEW analytics.vw_fato_enriquecido AS
SELECT
    f.fact_id,
    f.valor,
    f.ano_origem,
    t.tempo_id, t.data_referencia, t.ano, t.mes, t.trimestre, t.nome_mes, t.is_partial_year,
    l.localidade_id, l.uf, l.municipio, l.regiao,
    i.indicador_id, i.evento, i.familia_medida, i.unidade, i.tipo_indicador,
    -- grupo_semantico: o agrupamento de 5 categorias pedido na Fase 2
    -- (vítimas / ocorrências / ações policiais / apreensões / pesos), derivado
    -- de tipo_indicador (Fase 0.5/1). Nunca persiste em dim_indicador — é
    -- calculado aqui para não alterar o esquema da Fase 1.
    CASE
        WHEN i.tipo_indicador LIKE 'Vítima%' OR i.tipo_indicador LIKE 'Pessoa%' THEN 'Vítimas'
        WHEN i.tipo_indicador = 'Ação Policial' THEN 'Ações Policiais'
        WHEN i.tipo_indicador LIKE 'Ocorrência%' THEN 'Ocorrências'
        WHEN i.tipo_indicador = 'Apreensão - Peso' THEN 'Apreensões (Peso)'
        WHEN i.tipo_indicador = 'Apreensão - Unidade' THEN 'Apreensões (Unidade)'
        WHEN i.tipo_indicador LIKE 'Serviço%' THEN 'Serviços'
        ELSE 'Outro'
    END AS grupo_semantico,
    ab.abrangencia_id, ab.abrangencia,
    ag.agente_id, ag.agente,
    ar.arma_id, ar.arma,
    fe.faixa_etaria_id, fe.faixa_etaria,
    s.sexo_id, s.sexo
FROM fact_indicadores f
JOIN dim_tempo t        ON f.tempo_id = t.tempo_id
JOIN dim_localidade l   ON f.localidade_id = l.localidade_id
JOIN dim_indicador i    ON f.indicador_id = i.indicador_id
JOIN dim_abrangencia ab ON f.abrangencia_id = ab.abrangencia_id
LEFT JOIN dim_agente ag       ON f.agente_id = ag.agente_id
LEFT JOIN dim_arma ar         ON f.arma_id = ar.arma_id
LEFT JOIN dim_faixa_etaria fe ON f.faixa_etaria_id = fe.faixa_etaria_id
LEFT JOIN dim_sexo s          ON f.sexo_id = s.sexo_id;

COMMENT ON VIEW analytics.vw_fato_enriquecido IS
'Camada semântica base do ATLAS. Toda métrica derivada desta view carrega evento/familia_medida/unidade/grupo_semantico — nunca agregar valor sem GROUP BY incluindo pelo menos familia_medida (idealmente evento), sob risco de somar pessoas + ocorrências + kg.';
