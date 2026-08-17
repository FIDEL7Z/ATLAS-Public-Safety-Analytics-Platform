-- ATLAS — Fase 2 — 11: Análise de pesos (Apreensão de Cocaína/Maconha) e
-- impacto de outliers. Os valores extremos NUNCA são removidos da base —
-- estas views existem para EXPOR o efeito deles na média/soma, não para
-- escondê-lo (Fase 0.5 §6 e regra 8/9 da Fase 1).

DROP VIEW IF EXISTS analytics.vw_pesos_percentis CASCADE;
CREATE VIEW analytics.vw_pesos_percentis AS
SELECT
    evento, ano, unidade,
    COUNT(*) AS n_registros,
    SUM(valor) AS soma,
    AVG(valor) AS media,
    PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY valor) AS mediana,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY valor) AS p90,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY valor) AS p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY valor) AS p99,
    MAX(valor) AS maximo
FROM analytics.vw_fato_enriquecido
WHERE familia_medida = 'peso'
GROUP BY evento, ano, unidade;

COMMENT ON VIEW analytics.vw_pesos_percentis IS
'11 — soma/média/mediana/P90/P95/P99/máximo de Apreensão de Cocaína e Maconha, por ano. Unidade herdada de dim_indicador ("kg, não confirmado pela fonte" — Fase 0.5 §6) — nunca convertida.';

-- Demonstra o efeito dos outliers sobre média e soma SEM remover nenhum
-- valor da base: compara a métrica "com tudo" contra a métrica recalculada
-- excluindo apenas o 1% mais extremo (> P99), lado a lado.
DROP VIEW IF EXISTS analytics.vw_pesos_impacto_outliers CASCADE;
CREATE VIEW analytics.vw_pesos_impacto_outliers AS
WITH p99_por_evento AS (
    SELECT evento, PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY valor) AS p99
    FROM analytics.vw_fato_enriquecido
    WHERE familia_medida = 'peso'
    GROUP BY evento
)
SELECT
    e.evento,
    COUNT(*) AS n_registros_total,
    COUNT(*) FILTER (WHERE e.valor > p.p99) AS n_registros_acima_p99,
    AVG(e.valor) AS media_com_outliers,
    AVG(e.valor) FILTER (WHERE e.valor <= p.p99) AS media_sem_top1pct,
    SUM(e.valor) AS soma_com_outliers,
    SUM(e.valor) FILTER (WHERE e.valor <= p.p99) AS soma_sem_top1pct,
    ROUND(
        100.0 * (AVG(e.valor) - AVG(e.valor) FILTER (WHERE e.valor <= p.p99))
        / NULLIF(AVG(e.valor) FILTER (WHERE e.valor <= p.p99), 0),
        1
    ) AS impacto_pct_na_media
FROM analytics.vw_fato_enriquecido e
JOIN p99_por_evento p ON e.evento = p.evento
WHERE e.familia_medida = 'peso'
GROUP BY e.evento;

COMMENT ON VIEW analytics.vw_pesos_impacto_outliers IS
'Quantifica o quanto o 1% mais extremo de apreensões infla a média — apenas para leitura comparativa. A base (fact_indicadores) permanece 100% intacta; nada é filtrado fora desta view.';
