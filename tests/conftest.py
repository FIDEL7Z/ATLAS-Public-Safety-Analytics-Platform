"""Fixture sintética que reproduz, em escala pequena, os padrões críticos
encontrados nos dados reais do Sinesp VDE (Fases 0 / 0.5):

- Registros "duplicados" na mesma chave dimensional (padrão DF) que devem
  ser somados, nunca descartados.
- Um valor "não informado" dentro de uma família aplicável (não deve virar
  fact row com 0, nem quebrar o pipeline).
- As 3 famílias de medida (vitima / contagem / peso).
- Uso de agente, arma e faixa_etaria como parte do grão.
- Um ano completo (12 meses) e um ano parcial (3 meses), para testar a flag
  is_partial_year.
"""
from datetime import date

import pandas as pd
import pytest

RAW_COLUMNS = [
    "uf", "municipio", "evento", "data_referencia", "agente", "arma",
    "faixa_etaria", "feminino", "masculino", "nao_informado", "total_vitima",
    "total", "total_peso", "abrangencia",
]


def _row(**kwargs) -> dict:
    base = dict.fromkeys(RAW_COLUMNS, None)
    base.update(kwargs)
    return base


def _filler_rows(ano: int, n_months: int) -> list[dict]:
    return [
        _row(
            uf="SP", municipio="CIDADE TESTE", evento="Homicídio doloso",
            data_referencia=date(ano, mes, 1),
            feminino=0.0, masculino=0.0, nao_informado=0.0, total_vitima=0.0,
            abrangencia="Estadual",
        )
        for mes in range(1, n_months + 1)
    ]


@pytest.fixture
def sample_raw_by_year() -> dict[int, pd.DataFrame]:
    ano_completo = 2030
    ano_parcial = 2031

    rows_2030 = _filler_rows(ano_completo, 12) + [
        # Padrão DF: duas linhas com a MESMA chave dimensional, valores
        # diferentes -> devem ser somadas (feminino=1, masculino=1).
        _row(
            uf="DF", municipio="BRASÍLIA", evento="Homicídio doloso",
            data_referencia=date(ano_completo, 1, 1),
            feminino=1.0, masculino=0.0, nao_informado=0.0, total_vitima=1.0,
            abrangencia="Estadual",
        ),
        _row(
            uf="DF", municipio="BRASÍLIA", evento="Homicídio doloso",
            data_referencia=date(ano_completo, 1, 1),
            feminino=0.0, masculino=1.0, nao_informado=0.0, total_vitima=1.0,
            abrangencia="Estadual",
        ),
        # Contagem "não informado": total ausente para um evento que É da
        # família contagem -> não deve virar linha na fact (nem 0).
        _row(
            uf="SP", municipio="OUTRACIDADE", evento="Mandado de prisão cumprido",
            data_referencia=date(ano_completo, 1, 1),
            total=None, abrangencia="Estadual",
        ),
        # Contagem normal.
        _row(
            uf="SP", municipio="OUTRACIDADE", evento="Mandado de prisão cumprido",
            data_referencia=date(ano_completo, 2, 1),
            total=5.0, abrangencia="Estadual",
        ),
        # Peso.
        _row(
            uf="SP", municipio="OUTRACIDADE", evento="Apreensão de Cocaína",
            data_referencia=date(ano_completo, 1, 1),
            total_peso=12.5, abrangencia="Estadual",
        ),
        # Arma — duas linhas mesma chave exceto `arma` (dimensão do grão,
        # não devem ser somadas entre si).
        _row(
            uf="SP", municipio="OUTRACIDADE", evento="Arma de Fogo Apreendida",
            data_referencia=date(ano_completo, 1, 1),
            arma="Pistola", total=3.0, abrangencia="Estadual",
        ),
        _row(
            uf="SP", municipio="OUTRACIDADE", evento="Arma de Fogo Apreendida",
            data_referencia=date(ano_completo, 1, 1),
            arma="Fuzil", total=2.0, abrangencia="Estadual",
        ),
        # Faixa etária.
        _row(
            uf="SP", municipio="OUTRACIDADE", evento="Pessoa Desaparecida",
            data_referencia=date(ano_completo, 1, 1),
            faixa_etaria="Maior de Idade", feminino=1.0, masculino=0.0,
            nao_informado=0.0, total_vitima=1.0, abrangencia="Estadual",
        ),
        # Agente.
        _row(
            uf="SP", municipio="OUTRACIDADE", evento="Morte de Agente do Estado",
            data_referencia=date(ano_completo, 1, 1),
            agente="Polícia Militar", feminino=0.0, masculino=1.0,
            nao_informado=0.0, total_vitima=1.0, abrangencia="Estadual",
        ),
    ]

    rows_2031 = _filler_rows(ano_parcial, 3)

    return {
        ano_completo: pd.DataFrame(rows_2030)[RAW_COLUMNS],
        ano_parcial: pd.DataFrame(rows_2031)[RAW_COLUMNS],
    }
