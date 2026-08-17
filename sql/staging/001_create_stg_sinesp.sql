-- ATLAS — Public Safety Analytics Platform
-- Staging layer: 1:1 normalized representation of the raw Sinesp VDE extracts.
-- No aggregation, no deduplication, no derived columns here (total_vitima is
-- intentionally excluded — it is always derivable as feminino+masculino+nao_informado
-- and must never be stored, per the Fase 0.5 model validation).

DROP TABLE IF EXISTS stg_sinesp;

CREATE TABLE stg_sinesp (
    uf              CHAR(2)         NOT NULL,
    municipio       VARCHAR(120)    NOT NULL,
    evento          VARCHAR(120)    NOT NULL,
    data_referencia DATE            NOT NULL,
    agente          VARCHAR(60),        -- NULL = não aplicável a este evento
    arma            VARCHAR(60),        -- NULL = não aplicável a este evento
    faixa_etaria    VARCHAR(60),        -- NULL = não aplicável a este evento
    feminino        NUMERIC(12, 3),     -- NULL = não aplicável (evento não é da família "vítima")
    masculino       NUMERIC(12, 3),
    nao_informado   NUMERIC(12, 3),
    total           NUMERIC(12, 3),     -- NULL = não aplicável (evento não é da família "contagem")
    total_peso      NUMERIC(14, 3),     -- NULL = não aplicável (evento não é da família "peso")
    abrangencia     VARCHAR(40)     NOT NULL,
    ano_origem      SMALLINT        NOT NULL    -- ano do arquivo fonte (BancoVDE <ano>.xlsx)
);

CREATE INDEX ix_stg_sinesp_ano ON stg_sinesp (ano_origem);
CREATE INDEX ix_stg_sinesp_evento ON stg_sinesp (evento);
CREATE INDEX ix_stg_sinesp_uf ON stg_sinesp (uf);

COMMENT ON TABLE stg_sinesp IS 'Camada staging: cópia normalizada e tipada dos 3 arquivos BancoVDE, sem nenhuma linha removida ou agregada. Registros aparentemente duplicados são preservados aqui (a agregação por grão real ocorre apenas na camada de transformação).';
