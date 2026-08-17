"""Tabelas de referência estáticas usadas na construção das dimensões.

Estas tabelas NÃO são inventadas: a classificação semântica dos 31 eventos
foi derivada exclusivamente da observação do comportamento das colunas nos
3 arquivos fonte (Fase 0.5 — ver docs/MODEL_VALIDATION.md, seção 3). O
mapeamento UF -> Região é a divisão oficial do IBGE (não presente na fonte,
mas estável e pública) e é a única informação externa introduzida no
pipeline.

Se um novo `evento` aparecer em uma carga futura sem estar mapeado aqui, o
pipeline falha explicitamente (ver validate_evento_coverage) em vez de
seguir em frente com uma classificação inventada.
"""
import pandas as pd

# familia_medida: qual coluna de origem popula o `valor` deste indicador.
#   'vitima'   -> feminino / masculino / nao_informado (unpivot em sexo)
#   'contagem' -> total
#   'peso'     -> total_peso
#
# unidade: unidade de medida observada/inferida (nunca convertida).
# tipo_indicador: categoria de negócio (para filtros/dashboards).
INDICADOR_CLASSIFICATION: dict[str, dict[str, str]] = {
    "Feminicídio": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Violência Letal Intencional"),
    "Tentativa de feminicídio": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Tentativa de Violência Letal"),
    "Homicídio doloso": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Violência Letal Intencional"),
    "Tentativa de homicídio": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Tentativa de Violência Letal"),
    "Lesão corporal seguida de morte": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Violência Letal Intencional"),
    "Roubo seguido de morte (latrocínio)": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Violência Letal Intencional"),
    "Mortes a esclarecer (sem indício de crime)": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - A Esclarecer"),
    "Morte no trânsito ou em decorrência dele (exceto homicídio doloso)": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Trânsito"),
    "Mortes no trânsito": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Trânsito"),
    "Suicídio": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Autoprovocada"),
    "Estupro": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Violência Sexual"),
    "Estupro de vulnerável": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Violência Sexual"),
    "Morte de Agente do Estado": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Agente do Estado (óbito do agente)"),
    "Suicídio de Agente do Estado": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Agente do Estado (óbito do agente)"),
    "Morte por intervenção de Agente do Estado": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Vítima - Letalidade Policial (civil morto por agente)"),
    "Pessoa Desaparecida": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Pessoa - Desaparecimento"),
    "Pessoa Localizada": dict(familia_medida="vitima", unidade="pessoas", tipo_indicador="Pessoa - Desaparecimento (Resolução)"),
    "Mandado de prisão cumprido": dict(familia_medida="contagem", unidade="mandados", tipo_indicador="Ação Policial"),
    "Arma de Fogo Apreendida": dict(familia_medida="contagem", unidade="armas (unidades)", tipo_indicador="Apreensão - Unidade"),
    "Furto de veículo": dict(familia_medida="contagem", unidade="ocorrências", tipo_indicador="Ocorrência - Patrimonial"),
    "Roubo de veículo": dict(familia_medida="contagem", unidade="ocorrências", tipo_indicador="Ocorrência - Patrimonial"),
    "Roubo de carga": dict(familia_medida="contagem", unidade="ocorrências", tipo_indicador="Ocorrência - Patrimonial"),
    "Roubo a instituição financeira": dict(familia_medida="contagem", unidade="ocorrências", tipo_indicador="Ocorrência - Patrimonial"),
    "Tráfico de drogas": dict(familia_medida="contagem", unidade="ocorrências", tipo_indicador="Ocorrência - Criminal (Drogas)"),
    "Apreensão de Cocaína": dict(familia_medida="peso", unidade="kg (não confirmado pela fonte)", tipo_indicador="Apreensão - Peso"),
    "Apreensão de Maconha": dict(familia_medida="peso", unidade="kg (não confirmado pela fonte)", tipo_indicador="Apreensão - Peso"),
    "Atendimento pré-hospitalar": dict(familia_medida="contagem", unidade="atendimentos", tipo_indicador="Serviço - Saúde/Resgate"),
    "Busca e salvamento": dict(familia_medida="contagem", unidade="operações", tipo_indicador="Serviço - Resgate"),
    "Combate a incêndios": dict(familia_medida="contagem", unidade="ocorrências", tipo_indicador="Serviço - Bombeiros"),
    "Emissão de Alvarás de licença": dict(familia_medida="contagem", unidade="alvarás", tipo_indicador="Serviço - Administrativo"),
    "Realização de vistorias": dict(familia_medida="contagem", unidade="vistorias", tipo_indicador="Serviço - Administrativo"),
}

UF_REGIAO: dict[str, str] = {
    # Norte
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
    # Nordeste
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste",
    "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    # Centro-Oeste
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MS": "Centro-Oeste", "MT": "Centro-Oeste",
    # Sudeste
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    # Sul
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}


def validate_evento_coverage(eventos_presentes: set[str]) -> None:
    nao_mapeados = eventos_presentes - set(INDICADOR_CLASSIFICATION)
    if nao_mapeados:
        raise ValueError(
            "Eventos presentes na fonte sem classificação semântica definida em "
            f"reference_data.INDICADOR_CLASSIFICATION: {sorted(nao_mapeados)}. "
            "Não prosseguir com uma classificação inventada — atualizar a tabela "
            "de referência com base em observação real dos dados antes de rodar o ETL."
        )


def validate_uf_coverage(ufs_presentes: set[str]) -> None:
    nao_mapeadas = ufs_presentes - set(UF_REGIAO)
    if nao_mapeadas:
        raise ValueError(f"UFs presentes na fonte sem região mapeada: {sorted(nao_mapeadas)}")


def indicador_classification_df() -> pd.DataFrame:
    rows = [
        {"evento": evento, **attrs}
        for evento, attrs in INDICADOR_CLASSIFICATION.items()
    ]
    return pd.DataFrame(rows)
