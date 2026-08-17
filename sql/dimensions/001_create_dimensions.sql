-- ATLAS — Public Safety Analytics Platform
-- Dimension tables for the long-format star schema (fact_indicadores).
-- Surrogate keys are assigned deterministically by the Python transformation
-- layer (sorted unique values -> sequential integer), not by DB sequences,
-- so IDs are reproducible across ETL runs given the same source data.

DROP TABLE IF EXISTS dim_tempo CASCADE;
DROP TABLE IF EXISTS dim_localidade CASCADE;
DROP TABLE IF EXISTS dim_indicador CASCADE;
DROP TABLE IF EXISTS dim_abrangencia CASCADE;
DROP TABLE IF EXISTS dim_agente CASCADE;
DROP TABLE IF EXISTS dim_arma CASCADE;
DROP TABLE IF EXISTS dim_faixa_etaria CASCADE;
DROP TABLE IF EXISTS dim_sexo CASCADE;

CREATE TABLE dim_tempo (
    tempo_id        INTEGER PRIMARY KEY,
    data_referencia DATE UNIQUE NOT NULL,
    ano             SMALLINT NOT NULL,
    mes             SMALLINT NOT NULL,
    trimestre       SMALLINT NOT NULL,
    nome_mes        VARCHAR(20) NOT NULL,
    is_partial_year BOOLEAN NOT NULL   -- TRUE quando o ano de origem tem < 12 meses reportados na fonte
);

CREATE TABLE dim_localidade (
    localidade_id   INTEGER PRIMARY KEY,
    uf              CHAR(2) NOT NULL,
    municipio       VARCHAR(120) NOT NULL,
    regiao          VARCHAR(20) NOT NULL,  -- derivado do mapeamento oficial IBGE UF -> Região (não presente na fonte)
    UNIQUE (uf, municipio)
);

CREATE TABLE dim_indicador (
    indicador_id    INTEGER PRIMARY KEY,
    evento          VARCHAR(120) UNIQUE NOT NULL,
    familia_medida  VARCHAR(20) NOT NULL,   -- 'vitima' | 'contagem' | 'peso' — família técnica (qual coluna de origem popula o valor)
    unidade         VARCHAR(40) NOT NULL,   -- pessoas | ocorrências | kg (não confirmado) | armas (unidades) | mandados | atendimentos | operações | alvarás | vistorias
    tipo_indicador  VARCHAR(60) NOT NULL    -- categoria semântica de negócio (ver docs/MODEL_VALIDATION.md secao 3)
);

CREATE TABLE dim_abrangencia (
    abrangencia_id  INTEGER PRIMARY KEY,
    abrangencia     VARCHAR(40) UNIQUE NOT NULL
);

CREATE TABLE dim_agente (
    agente_id       INTEGER PRIMARY KEY,
    agente          VARCHAR(60) UNIQUE NOT NULL
);

CREATE TABLE dim_arma (
    arma_id         INTEGER PRIMARY KEY,
    arma            VARCHAR(60) UNIQUE NOT NULL
);

CREATE TABLE dim_faixa_etaria (
    faixa_etaria_id INTEGER PRIMARY KEY,
    faixa_etaria    VARCHAR(60) UNIQUE NOT NULL
);

CREATE TABLE dim_sexo (
    sexo_id         INTEGER PRIMARY KEY,
    sexo            VARCHAR(20) UNIQUE NOT NULL
);

COMMENT ON TABLE dim_indicador IS 'Classificação semântica dos 31 eventos, derivada exclusivamente da observação dos dados (Fase 0.5). familia_medida controla a unidade e a somabilidade dentro da própria família; tipo_indicador é a categoria de negócio usada nos filtros do dashboard.';
