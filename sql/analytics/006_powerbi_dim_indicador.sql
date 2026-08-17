-- ATLAS — Fase 3 — Dimensão de indicador pronta para o Power BI.
--
-- Por que uma view nova, e não importar dim_indicador puro?
-- grupo_semantico é uma CLASSIFICAÇÃO ESTRUTURAL (Vítimas/Ocorrências/Ações
-- Policiais/Apreensões-Peso/Apreensões-Unidade/Serviços) — pertence ao SQL,
-- não ao DAX, conforme o princípio fundamental da Fase 3 ("Power BI não deve
-- reproduzir lógica já existente no Postgres"). Sem esta view, cada relatório
-- Power BI reimplementaria a mesma lógica CASE em DAX, com risco de divergir
-- da classificação já validada na Fase 2.

DROP VIEW IF EXISTS analytics.vw_dim_indicador CASCADE;
CREATE VIEW analytics.vw_dim_indicador AS
SELECT
    indicador_id, evento, familia_medida, unidade, tipo_indicador,
    CASE
        WHEN tipo_indicador LIKE 'Vítima%' OR tipo_indicador LIKE 'Pessoa%' THEN 'Vítimas'
        WHEN tipo_indicador = 'Ação Policial' THEN 'Ações Policiais'
        WHEN tipo_indicador LIKE 'Ocorrência%' THEN 'Ocorrências'
        WHEN tipo_indicador = 'Apreensão - Peso' THEN 'Apreensões (Peso)'
        WHEN tipo_indicador = 'Apreensão - Unidade' THEN 'Apreensões (Unidade)'
        WHEN tipo_indicador LIKE 'Serviço%' THEN 'Serviços'
        ELSE 'Outro'
    END AS grupo_semantico
FROM dim_indicador;

COMMENT ON VIEW analytics.vw_dim_indicador IS
'Dimensão de indicador para import no Power BI — dim_indicador + grupo_semantico. É a tabela "Dim Indicador" do modelo semântico (docs/POWERBI_MODEL.md).';
