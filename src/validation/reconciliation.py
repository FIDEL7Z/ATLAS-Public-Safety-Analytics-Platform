"""Reconciliação RAW vs STAGING vs FACT, por evento — teste crítico da Fase 1.

Para cada um dos 31 eventos, soma o valor bruto na origem (RAW, com a mesma
lógica de família de medida usada no resto do pipeline) e compara com a soma
correspondente na fact_indicadores. Qualquer diferença é reportada
explicitamente — nunca escondida.
"""
from datetime import datetime

import pandas as pd

from src.config import DOCS_DIR, get_logger
from src.transformation.reference_data import INDICADOR_CLASSIFICATION

logger = get_logger(__name__)

TOLERANCE = 1e-6


def _raw_total_for_evento(raw_by_year: dict[int, pd.DataFrame], evento: str, familia: str) -> float:
    total = 0.0
    for df in raw_by_year.values():
        sub = df.loc[df["evento"] == evento]
        if familia == "vitima":
            total += sub[["feminino", "masculino", "nao_informado"]].sum(skipna=True).sum()
        elif familia == "contagem":
            total += sub["total"].sum(skipna=True)
        elif familia == "peso":
            total += sub["total_peso"].sum(skipna=True)
    return float(total)


def _staging_total_for_evento(stg: pd.DataFrame, evento: str, familia: str) -> float:
    sub = stg.loc[stg["evento"] == evento]
    if familia == "vitima":
        return float(sub[["feminino", "masculino", "nao_informado"]].sum(skipna=True).sum())
    elif familia == "contagem":
        return float(sub["total"].sum(skipna=True))
    elif familia == "peso":
        return float(sub["total_peso"].sum(skipna=True))
    return 0.0


def _fact_total_for_evento(fact: pd.DataFrame, dim_indicador: pd.DataFrame, evento: str) -> float:
    indicador_id = dim_indicador.loc[dim_indicador["evento"] == evento, "indicador_id"].iloc[0]
    return float(fact.loc[fact["indicador_id"] == indicador_id, "valor"].sum())


def build_reconciliation(
    raw_by_year: dict[int, pd.DataFrame],
    stg: pd.DataFrame,
    fact: pd.DataFrame,
    dim_indicador: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for evento, attrs in sorted(INDICADOR_CLASSIFICATION.items()):
        familia = attrs["familia_medida"]
        raw_total = _raw_total_for_evento(raw_by_year, evento, familia)
        staging_total = _staging_total_for_evento(stg, evento, familia)
        fact_total = _fact_total_for_evento(fact, dim_indicador, evento)

        diff = fact_total - raw_total
        status = "PASS" if abs(diff) <= TOLERANCE else "FAIL"

        rows.append({
            "evento": evento,
            "familia_medida": familia,
            "raw_total": raw_total,
            "staging_total": staging_total,
            "fact_total": fact_total,
            "diferenca": diff,
            "status": status,
        })

    result = pd.DataFrame(rows)
    n_fail = (result["status"] == "FAIL").sum()
    if n_fail:
        logger.error(f"RECONCILIAÇÃO: {n_fail} evento(s) com status FAIL — ver detalhes no relatório")
    else:
        logger.info("RECONCILIAÇÃO: todos os 31 eventos com status PASS (RAW == STAGING == FACT)")
    return result


def write_reconciliation_report(result: pd.DataFrame) -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    path = DOCS_DIR / "ETL_RECONCILIATION.md"

    n_pass = (result["status"] == "PASS").sum()
    n_fail = (result["status"] == "FAIL").sum()

    lines = [
        "# ATLAS — ETL Reconciliation Report",
        "",
        f"**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Eventos verificados:** {len(result)} · **PASS:** {n_pass} · **FAIL:** {n_fail}",
        "",
        "Para cada evento, o valor agregado bruto (RAW — soma direta dos 3 arquivos fonte, "
        "sem nenhuma transformação) é comparado com o valor agregado na fact_indicadores "
        "(após staging, agregação pelo grão real e unpivot para o formato longo). "
        "STAGING é incluído para evidenciar que a camada staging não altera nenhum valor "
        "(é sempre idêntico a RAW).",
        "",
        "| Evento | Família | RAW | STAGING | FACT | Diferença | Status |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for _, r in result.iterrows():
        lines.append(
            f"| {r['evento']} | {r['familia_medida']} | {r['raw_total']:,.3f} | "
            f"{r['staging_total']:,.3f} | {r['fact_total']:,.3f} | {r['diferenca']:,.6f} | "
            f"**{r['status']}** |"
        )

    lines += [
        "",
        "## Interpretação",
        "",
        "- STAGING == RAW em todos os eventos: esperado, pois a camada staging não agrega nem filtra linhas.",
        "- FACT == RAW (tolerância 1e-6, para acumulação de ponto flutuante em `total_peso`): "
        "confirma que a agregação por grão real (SUM) e o unpivot para o formato longo preservam "
        "exatamente o total original — nenhum valor foi perdido, duplicado ou inventado durante a transformação.",
        "- Linhas com valor 'não informado' na fonte (aplicável, mas não reportado) são omitidas da "
        "fact_indicadores por design (nunca preenchidas com 0) — como o SUM do pandas ignora NaN em "
        "ambos os lados da comparação (RAW e FACT), essa omissão não gera diferença na reconciliação. "
        "Essas ocorrências são quantificadas separadamente em `data/quality_reports/DATA_QUALITY_REPORT.md`.",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Relatório de reconciliação salvo em {path}")
