"""Validações de qualidade pós-transformação (Fase 1).

Cada check retorna um dict com status PASS/FAIL/INFO e detalhes. O relatório
final é escrito em data/quality_reports/DATA_QUALITY_REPORT.md.
"""
from datetime import datetime

import pandas as pd

from src.config import DATA_QUALITY_DIR, MONTHS_PER_FULL_YEAR, get_logger

logger = get_logger(__name__)

GRAIN_ID_COLS = [
    "tempo_id", "localidade_id", "indicador_id", "abrangencia_id",
    "agente_id", "arma_id", "faixa_etaria_id", "sexo_id",
]


def check_grain_uniqueness(fact: pd.DataFrame) -> dict:
    key = fact[GRAIN_ID_COLS].astype("Int64").fillna(-1)
    n_dup = key.duplicated(keep=False).sum()
    return {
        "check": "Duplicidade no grão final da fact_indicadores",
        "status": "PASS" if n_dup == 0 else "FAIL",
        "detalhe": f"{n_dup:,} linhas com chave de grão duplicada (esperado: 0)",
    }


def check_no_negative_values(fact: pd.DataFrame) -> dict:
    n_neg = (fact["valor"] < 0).sum()
    return {
        "check": "Valores negativos em `valor`",
        "status": "PASS" if n_neg == 0 else "FAIL",
        "detalhe": f"{n_neg:,} linhas com valor negativo (esperado: 0)",
    }


def check_mandatory_fields_not_null(fact: pd.DataFrame) -> dict:
    mandatory = ["tempo_id", "localidade_id", "indicador_id", "abrangencia_id", "valor"]
    nulls = {c: int(fact[c].isna().sum()) for c in mandatory}
    n_total_nulls = sum(nulls.values())
    return {
        "check": "Campos obrigatórios sem nulos (tempo/localidade/indicador/abrangencia/valor)",
        "status": "PASS" if n_total_nulls == 0 else "FAIL",
        "detalhe": f"nulos por campo: {nulls}",
    }


def check_sexo_consistency(fact: pd.DataFrame, dim_indicador: pd.DataFrame) -> dict:
    fact_ind = fact.merge(dim_indicador[["indicador_id", "familia_medida"]], on="indicador_id", how="left")

    vitima_sem_sexo = fact_ind[(fact_ind["familia_medida"] == "vitima") & fact_ind["sexo_id"].isna()]
    nao_vitima_com_sexo = fact_ind[(fact_ind["familia_medida"] != "vitima") & fact_ind["sexo_id"].notna()]

    ok = len(vitima_sem_sexo) == 0 and len(nao_vitima_com_sexo) == 0
    return {
        "check": "Consistência de sexo (vitima sempre tem sexo_id; contagem/peso nunca têm)",
        "status": "PASS" if ok else "FAIL",
        "detalhe": (
            f"linhas 'vitima' sem sexo_id: {len(vitima_sem_sexo):,} (esperado 0); "
            f"linhas não-'vitima' com sexo_id: {len(nao_vitima_com_sexo):,} (esperado 0)"
        ),
    }


def check_indicador_family_consistency(fact: pd.DataFrame, dim_indicador: pd.DataFrame) -> dict:
    """Cada indicador só pode aparecer na fact com a familia_medida esperada
    (nenhum indicador 'vitima' contribuindo para um total tipicamente
    'contagem', e vice-versa) — valida a regra 'não misturar semanticamente'."""
    fact_ind = fact.merge(dim_indicador[["indicador_id", "evento", "familia_medida"]], on="indicador_id", how="left")
    problemas = []
    for indicador_id, g in fact_ind.groupby("indicador_id"):
        familias_no_fato = set(g["familia_medida"].unique())
        if len(familias_no_fato) != 1:
            problemas.append((g["evento"].iloc[0], familias_no_fato))
    return {
        "check": "Cada indicador pertence a exatamente uma família de medida na fact table",
        "status": "PASS" if not problemas else "FAIL",
        "detalhe": f"indicadores com mistura de família: {problemas}" if problemas else "nenhuma mistura encontrada",
    }


def check_unidade_consistency(dim_indicador: pd.DataFrame) -> dict:
    vazios = dim_indicador["unidade"].isna().sum() + (dim_indicador["unidade"].str.strip() == "").sum()
    return {
        "check": "Toda linha de dim_indicador tem `unidade` preenchida",
        "status": "PASS" if vazios == 0 else "FAIL",
        "detalhe": f"{vazios} linha(s) de dim_indicador sem unidade definida",
    }


def check_temporal_consistency(dim_tempo: pd.DataFrame) -> dict:
    problemas = []
    for ano, g in dim_tempo.groupby("ano"):
        n_meses = len(g)
        esperado_parcial = n_meses < MONTHS_PER_FULL_YEAR
        flag = g["is_partial_year"].unique()
        if len(flag) != 1 or bool(flag[0]) != esperado_parcial:
            problemas.append(f"ano {ano}: {n_meses} meses, is_partial_year={flag} (esperado {esperado_parcial})")
        meses_presentes = sorted(g["mes"].tolist())
        meses_esperados = list(range(1, n_meses + 1))
        if meses_presentes != meses_esperados:
            problemas.append(f"ano {ano}: meses não são um intervalo contínuo a partir de janeiro: {meses_presentes}")

    dup_datas = dim_tempo["data_referencia"].duplicated().sum()
    if dup_datas:
        problemas.append(f"{dup_datas} data(s) duplicada(s) em dim_tempo")

    return {
        "check": "Consistência temporal (meses contínuos por ano, flag is_partial_year correta)",
        "status": "PASS" if not problemas else "FAIL",
        "detalhe": "; ".join(problemas) if problemas else "ok",
    }


def check_row_counts(n_raw: int, n_staging: int) -> dict:
    return {
        "check": "STAGING preserva 100% das linhas do RAW",
        "status": "PASS" if n_raw == n_staging else "FAIL",
        "detalhe": f"RAW={n_raw:,} STAGING={n_staging:,}",
    }


def run_all_checks(
    n_raw: int,
    stg: pd.DataFrame,
    fact: pd.DataFrame,
    dims: dict[str, pd.DataFrame],
) -> list[dict]:
    checks = [
        check_row_counts(n_raw, len(stg)),
        check_grain_uniqueness(fact),
        check_no_negative_values(fact),
        check_mandatory_fields_not_null(fact),
        check_sexo_consistency(fact, dims["dim_indicador"]),
        check_indicador_family_consistency(fact, dims["dim_indicador"]),
        check_unidade_consistency(dims["dim_indicador"]),
        check_temporal_consistency(dims["dim_tempo"]),
    ]
    for c in checks:
        level = logger.info if c["status"] == "PASS" else logger.error
        level(f"DQ CHECK [{c['status']}] {c['check']} — {c['detalhe']}")
    return checks


def write_data_quality_report(
    checks: list[dict],
    nao_informado_stats: pd.DataFrame,
    row_counts: dict[str, int],
) -> None:
    DATA_QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_QUALITY_DIR / "DATA_QUALITY_REPORT.md"

    n_pass = sum(1 for c in checks if c["status"] == "PASS")
    n_fail = sum(1 for c in checks if c["status"] == "FAIL")

    lines = [
        "# ATLAS — Data Quality Report (pós-transformação)",
        "",
        f"**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Checks executados:** {len(checks)} · **PASS:** {n_pass} · **FAIL:** {n_fail}",
        "",
        "## Contagem de registros por camada",
        "",
        "| Camada | Linhas |",
        "|---|---:|",
    ]
    for k, v in row_counts.items():
        lines.append(f"| {k} | {v:,} |")

    lines += ["", "## Checks estruturais", "", "| Check | Status | Detalhe |", "|---|---|---|"]
    for c in checks:
        lines.append(f"| {c['check']} | **{c['status']}** | {c['detalhe']} |")

    lines += [
        "",
        "## 'Não informado' dentro da família aplicável (por evento)",
        "",
        "Diferente de 'não aplicável' (estrutural, esperado — ex.: `total` nulo para "
        "eventos da família vítima), estes são casos em que o evento pertence à "
        "família de medida, mas o valor específico não foi reportado pela fonte para "
        "aquela combinação de UF/Município/Mês/Abrangência (e demais dimensões "
        "aplicáveis). Essas linhas **não são carregadas** na fact_indicadores (nunca "
        "preenchidas com 0) e são quantificadas aqui para transparência.",
        "",
        "| Evento | Família | Linhas de grão real | Valores aplicáveis | Não informados | % |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, r in nao_informado_stats.iterrows():
        lines.append(
            f"| {r['evento']} | {r['familia_medida']} | {r['linhas_grao_real']:,} | "
            f"{r['valores_aplicaveis']:,} | {r['valores_nao_informados']:,} | {r['pct_nao_informado']:.2f}% |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Relatório de qualidade salvo em {path}")
