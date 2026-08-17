"""Construção da fact_indicadores (formato longo).

Pipeline, nesta ordem:

1. AGREGAÇÃO pelo grão real validado (Fase 0.5):
   uf, municipio, evento, data_referencia, abrangencia, agente, arma,
   faixa_etaria, ano_origem
   Usa SUM (nunca DROP DUPLICATES — regra 1 da Fase 1) com min_count=1, para
   que uma célula onde TODAS as linhas de origem são nulas continue nula
   (distinção entre "soma zero" e "não informado" é preservada).

2. UNPIVOT para o formato longo: cada uma das 5 colunas de medida
   (feminino, masculino, nao_informado, total, total_peso) vira, quando
   não-nula, uma linha de fato independente. Uma célula nula é OMITIDA da
   fact table (nunca preenchida com 0 ou qualquer valor inventado — regra 4),
   e contabilizada separadamente para o relatório de qualidade.

   IMPORTANTE: o nulo pode ter duas causas distintas, ambas tratadas da
   mesma forma na fact table (omitir a linha), mas contadas separadamente:
     a) "não aplicável"  — o evento não pertence à família daquela coluna
        (ex.: `total` é sempre nulo para eventos da família "vitima").
        Fenômeno estrutural, 100% esperado.
     b) "não informado"  — o evento pertence à família daquela coluna, mas
        o valor não foi reportado para esta combinação específica de
        dimensões. Fenômeno real, verificado nos dados (1,8%-8,3% dentro da
        família aplicável — ver docs/DATA_QUALITY_REPORT.md).

3. `total_vitima` nunca é calculado nem carregado como medida própria — ele é
   sempre SUM(valor) das 3 linhas de sexo, sem filtro de sexo, calculado sob
   demanda na camada analítica (regra da Fase 0.5).
"""
import pandas as pd

from src.config import get_logger
from src.transformation.dimensions import SEXO_FEMININO, SEXO_MASCULINO, SEXO_NAO_INFORMADO

logger = get_logger(__name__)

GRAIN_COLS = [
    "uf", "municipio", "evento", "data_referencia", "abrangencia",
    "agente", "arma", "faixa_etaria", "ano_origem",
]
MEASURE_COLS = ["feminino", "masculino", "nao_informado", "total", "total_peso"]


def aggregate_to_real_grain(stg: pd.DataFrame) -> pd.DataFrame:
    """Agrega staging pelo grão real completo. SUM, nunca dedup."""
    grouped = stg.groupby(GRAIN_COLS, dropna=False, sort=False, observed=True)
    agg = grouped[MEASURE_COLS].sum(min_count=1).reset_index()

    logger.info(
        f"Agregação por grão real: {len(stg):,} linhas STAGING -> {len(agg):,} linhas de grão único "
        f"({len(stg) - len(agg):,} linhas combinadas por SUM dentro da mesma chave dimensional)"
    )
    return agg


def _map_surrogate_key(df: pd.DataFrame, dim: pd.DataFrame, on: str, id_col: str) -> pd.Series:
    """Left-join que preserva NaN quando o valor de origem é nulo (não aplicável)."""
    merged = df[[on]].merge(dim[[on, id_col]], on=on, how="left")
    return merged[id_col]


def _unpivot_measure(
    agg: pd.DataFrame,
    value_col: str,
    sexo_label: str | None,
    localidade_id: pd.Series,
    tempo_id: pd.Series,
    indicador_id: pd.Series,
    abrangencia_id: pd.Series,
    agente_id: pd.Series,
    arma_id: pd.Series,
    faixa_etaria_id: pd.Series,
    sexo_id_map: dict[str, int] | None,
) -> pd.DataFrame:
    mask = agg[value_col].notna()
    if mask.sum() == 0:
        return pd.DataFrame(columns=[
            "tempo_id", "localidade_id", "indicador_id", "abrangencia_id",
            "agente_id", "arma_id", "faixa_etaria_id", "sexo_id", "valor", "ano_origem",
        ])

    out = pd.DataFrame({
        "tempo_id": tempo_id[mask].values,
        "localidade_id": localidade_id[mask].values,
        "indicador_id": indicador_id[mask].values,
        "abrangencia_id": abrangencia_id[mask].values,
        "agente_id": agente_id[mask].values,
        "arma_id": arma_id[mask].values,
        "faixa_etaria_id": faixa_etaria_id[mask].values,
        "sexo_id": (sexo_id_map[sexo_label] if sexo_label else pd.NA),
        "valor": agg.loc[mask, value_col].values,
        "ano_origem": agg.loc[mask, "ano_origem"].values,
    })
    return out


def build_fact_indicadores(agg: pd.DataFrame, dims: dict[str, pd.DataFrame]) -> pd.DataFrame:
    dim_tempo = dims["dim_tempo"]
    dim_localidade = dims["dim_localidade"]
    dim_indicador = dims["dim_indicador"]
    dim_abrangencia = dims["dim_abrangencia"]
    dim_agente = dims["dim_agente"]
    dim_arma = dims["dim_arma"]
    dim_faixa_etaria = dims["dim_faixa_etaria"]
    dim_sexo = dims["dim_sexo"]
    sexo_id_map = dict(zip(dim_sexo["sexo"], dim_sexo["sexo_id"]))

    tempo_id = _map_surrogate_key(agg.rename(columns={"data_referencia": "data_referencia"}), dim_tempo, "data_referencia", "tempo_id")

    localidade_key = agg[["uf", "municipio"]].merge(
        dim_localidade[["uf", "municipio", "localidade_id"]], on=["uf", "municipio"], how="left"
    )
    localidade_id = localidade_key["localidade_id"]

    indicador_id = agg[["evento"]].merge(dim_indicador[["evento", "indicador_id"]], on="evento", how="left")["indicador_id"]
    abrangencia_id = _map_surrogate_key(agg, dim_abrangencia, "abrangencia", "abrangencia_id")
    agente_id = _map_surrogate_key(agg, dim_agente, "agente", "agente_id")
    arma_id = _map_surrogate_key(agg, dim_arma, "arma", "arma_id")
    faixa_etaria_id = _map_surrogate_key(agg, dim_faixa_etaria, "faixa_etaria", "faixa_etaria_id")

    for name, s in [("localidade_id", localidade_id), ("indicador_id", indicador_id), ("abrangencia_id", abrangencia_id)]:
        if s.isna().any():
            raise AssertionError(f"{name} não pode ser nulo — falha ao mapear chave substituta (dimensão obrigatória)")

    parts = [
        _unpivot_measure(agg, "feminino", SEXO_FEMININO, localidade_id, tempo_id, indicador_id, abrangencia_id, agente_id, arma_id, faixa_etaria_id, sexo_id_map),
        _unpivot_measure(agg, "masculino", SEXO_MASCULINO, localidade_id, tempo_id, indicador_id, abrangencia_id, agente_id, arma_id, faixa_etaria_id, sexo_id_map),
        _unpivot_measure(agg, "nao_informado", SEXO_NAO_INFORMADO, localidade_id, tempo_id, indicador_id, abrangencia_id, agente_id, arma_id, faixa_etaria_id, sexo_id_map),
        _unpivot_measure(agg, "total", None, localidade_id, tempo_id, indicador_id, abrangencia_id, agente_id, arma_id, faixa_etaria_id, sexo_id_map),
        _unpivot_measure(agg, "total_peso", None, localidade_id, tempo_id, indicador_id, abrangencia_id, agente_id, arma_id, faixa_etaria_id, sexo_id_map),
    ]
    fact = pd.concat(parts, ignore_index=True)

    for c in ["tempo_id", "localidade_id", "indicador_id", "abrangencia_id"]:
        fact[c] = fact[c].astype("int64")
    for c in ["agente_id", "arma_id", "faixa_etaria_id", "sexo_id"]:
        fact[c] = fact[c].astype("Int64")
    fact["ano_origem"] = fact["ano_origem"].astype("int16")
    fact["valor"] = fact["valor"].astype("float64")

    if (fact["valor"] < 0).any():
        raise AssertionError("valor negativo encontrado na fact_indicadores — violação da regra 'sem valores negativos'")
    if fact["valor"].isna().any():
        raise AssertionError("valor nulo encontrado na fact_indicadores — linhas com valor ausente devem ser omitidas antes deste ponto, nunca carregadas")

    logger.info(f"fact_indicadores construída: {len(fact):,} linhas")
    return fact


def compute_nao_informado_stats(agg: pd.DataFrame, dim_indicador: pd.DataFrame) -> pd.DataFrame:
    """Para cada evento, conta quantas linhas de grão real ficaram sem valor
    reportado DENTRO da família aplicável (não aplicável != não informado)."""
    merged = agg.merge(dim_indicador[["evento", "familia_medida"]], on="evento", how="left")
    rows = []
    for evento, g in merged.groupby("evento", observed=True):
        familia = g["familia_medida"].iloc[0]
        if familia == "vitima":
            aplicavel = len(g) * 3  # feminino + masculino + nao_informado
            nao_informado = g[["feminino", "masculino", "nao_informado"]].isna().sum().sum()
        elif familia == "contagem":
            aplicavel = len(g)
            nao_informado = g["total"].isna().sum()
        elif familia == "peso":
            aplicavel = len(g)
            nao_informado = g["total_peso"].isna().sum()
        else:
            continue
        rows.append({
            "evento": evento,
            "familia_medida": familia,
            "linhas_grao_real": len(g),
            "valores_aplicaveis": aplicavel,
            "valores_nao_informados": int(nao_informado),
            "pct_nao_informado": round(100 * nao_informado / aplicavel, 2) if aplicavel else 0.0,
        })
    return pd.DataFrame(rows).sort_values("evento").reset_index(drop=True)
