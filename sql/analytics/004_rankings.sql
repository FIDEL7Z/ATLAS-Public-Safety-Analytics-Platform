-- ATLAS — Fase 2 — Rankings. Todos particionados por (evento, ano) — nunca
-- um ranking mistura indicadores de unidades diferentes, e a partição por
-- ano evita comparar 2026 parcial com anos completos dentro do mesmo ranking.

DROP VIEW IF EXISTS analytics.vw_ranking_uf CASCADE;
CREATE VIEW analytics.vw_ranking_uf AS
SELECT
    evento, familia_medida, unidade, ano, is_partial_year, uf, regiao,
    total,
    RANK() OVER (PARTITION BY evento, ano ORDER BY total DESC) AS ranking
FROM analytics.vw_uf;

COMMENT ON VIEW analytics.vw_ranking_uf IS 'Ranking de UFs por indicador/ano — mesma unidade sempre, nunca cross-indicador.';

DROP VIEW IF EXISTS analytics.vw_ranking_municipio CASCADE;
CREATE VIEW analytics.vw_ranking_municipio AS
SELECT
    evento, familia_medida, unidade, ano, is_partial_year, uf, municipio,
    total,
    RANK() OVER (PARTITION BY evento, ano ORDER BY total DESC) AS ranking
FROM analytics.vw_municipio
WHERE total > 0;  -- ranking de município com 5.597 localidades x 31 indicadores fica mais útil sem as posições de valor 0 empatadas

COMMENT ON VIEW analytics.vw_ranking_municipio IS 'Ranking de municípios por indicador/ano (apenas municípios com total > 0).';

DROP VIEW IF EXISTS analytics.vw_ranking_regiao CASCADE;
CREATE VIEW analytics.vw_ranking_regiao AS
SELECT
    evento, familia_medida, unidade, ano, is_partial_year, regiao,
    SUM(total) AS total,
    RANK() OVER (PARTITION BY evento, ano ORDER BY SUM(total) DESC) AS ranking
FROM analytics.vw_uf
GROUP BY evento, familia_medida, unidade, ano, is_partial_year, regiao;

COMMENT ON VIEW analytics.vw_ranking_regiao IS 'Ranking de regiões (agregando UFs) por indicador/ano.';

DROP VIEW IF EXISTS analytics.vw_ranking_indicador CASCADE;
CREATE VIEW analytics.vw_ranking_indicador AS
SELECT
    grupo_semantico, familia_medida, unidade, ano, evento,
    total,
    RANK() OVER (PARTITION BY grupo_semantico, ano ORDER BY total DESC) AS ranking
FROM analytics.vw_indicador;

COMMENT ON VIEW analytics.vw_ranking_indicador IS
'Ranking de indicadores DENTRO do mesmo grupo_semantico e ano (ex.: qual indicador de "Ocorrências" tem mais volume) — nunca cross-grupo, pois as unidades diferem.';

DROP VIEW IF EXISTS analytics.vw_ranking_abrangencia CASCADE;
CREATE VIEW analytics.vw_ranking_abrangencia AS
SELECT
    evento, familia_medida, unidade, ano, abrangencia,
    total,
    RANK() OVER (PARTITION BY evento, ano ORDER BY total DESC) AS ranking
FROM analytics.vw_abrangencia;

COMMENT ON VIEW analytics.vw_ranking_abrangencia IS 'Ranking de abrangências (Estadual/PF/PRF) por indicador/ano.';

-- Participação percentual por UF dentro do total nacional do indicador (útil
-- para mapas de "share" no Power BI).
DROP VIEW IF EXISTS analytics.vw_participacao_uf CASCADE;
CREATE VIEW analytics.vw_participacao_uf AS
SELECT
    evento, familia_medida, unidade, ano, is_partial_year, uf, regiao, total,
    ROUND(100.0 * total / NULLIF(SUM(total) OVER (PARTITION BY evento, ano), 0), 2) AS participacao_pct_nacional
FROM analytics.vw_uf;

COMMENT ON VIEW analytics.vw_participacao_uf IS 'Participação percentual de cada UF no total nacional do indicador/ano.';
