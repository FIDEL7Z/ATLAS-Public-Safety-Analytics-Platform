-- ATLAS — Public Safety Analytics Platform
-- Fact table in LONG format. Grain (one row =):
--   tempo x localidade x indicador x abrangencia x [agente] x [arma] x [faixa_etaria] x [sexo]
--
-- IMPORTANT — this table does NOT store total_vitima. When an indicador belongs
-- to the "vitima" familia_medida, it is represented as up to 3 rows (sexo =
-- Feminino / Masculino / Nao Informado), each carrying its own `valor`.
-- "Total de vitimas" for such an indicador is always SUM(valor) with no sexo
-- filter — never a stored column — to avoid double counting (see
-- docs/MODEL_VALIDATION.md secao 4).
--
-- agente_id / arma_id / faixa_etaria_id / sexo_id are NULLABLE by design:
-- NULL means "não aplicável a este indicador", mirroring the semantics of the
-- source NULLs exactly (regra 4 da Fase 1) — no sentinel/invented category is used.

DROP TABLE IF EXISTS fact_indicadores;

CREATE TABLE fact_indicadores (
    fact_id         BIGSERIAL PRIMARY KEY,
    tempo_id        INTEGER NOT NULL REFERENCES dim_tempo(tempo_id),
    localidade_id   INTEGER NOT NULL REFERENCES dim_localidade(localidade_id),
    indicador_id    INTEGER NOT NULL REFERENCES dim_indicador(indicador_id),
    abrangencia_id  INTEGER NOT NULL REFERENCES dim_abrangencia(abrangencia_id),
    agente_id       INTEGER REFERENCES dim_agente(agente_id),
    arma_id         INTEGER REFERENCES dim_arma(arma_id),
    faixa_etaria_id INTEGER REFERENCES dim_faixa_etaria(faixa_etaria_id),
    sexo_id         INTEGER REFERENCES dim_sexo(sexo_id),
    valor           NUMERIC(14, 3) NOT NULL CHECK (valor >= 0),
    ano_origem      SMALLINT NOT NULL   -- preserva o ano do arquivo fonte (regra 10), redundante com dim_tempo.ano por conveniência de filtro direto
);

CREATE INDEX ix_fact_tempo ON fact_indicadores (tempo_id);
CREATE INDEX ix_fact_localidade ON fact_indicadores (localidade_id);
CREATE INDEX ix_fact_indicador ON fact_indicadores (indicador_id);
CREATE INDEX ix_fact_abrangencia ON fact_indicadores (abrangencia_id);
CREATE INDEX ix_fact_ano_origem ON fact_indicadores (ano_origem);

-- Garante que o grão real (validado na Fase 0.5) nunca é violado por carga duplicada:
-- uma combinação completa de dimensões (incluindo as condicionais) é única.
CREATE UNIQUE INDEX ux_fact_grain ON fact_indicadores (
    tempo_id, localidade_id, indicador_id, abrangencia_id,
    COALESCE(agente_id, -1), COALESCE(arma_id, -1),
    COALESCE(faixa_etaria_id, -1), COALESCE(sexo_id, -1)
);
