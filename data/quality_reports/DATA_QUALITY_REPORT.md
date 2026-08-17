# ATLAS — Data Quality Report (pós-transformação)

**Gerado em:** 2026-08-16 19:31:52
**Checks executados:** 8 · **PASS:** 8 · **FAIL:** 0

## Contagem de registros por camada

| Camada | Linhas |
|---|---:|
| RAW (soma dos 3 arquivos) | 1,996,058 |
| STAGING (stg_sinesp) | 1,996,058 |
| Grão real agregado (intermediário) | 1,984,506 |
| FACT (fact_indicadores, formato longo) | 5,291,040 |

## Checks estruturais

| Check | Status | Detalhe |
|---|---|---|
| STAGING preserva 100% das linhas do RAW | **PASS** | RAW=1,996,058 STAGING=1,996,058 |
| Duplicidade no grão final da fact_indicadores | **PASS** | 0 linhas com chave de grão duplicada (esperado: 0) |
| Valores negativos em `valor` | **PASS** | 0 linhas com valor negativo (esperado: 0) |
| Campos obrigatórios sem nulos (tempo/localidade/indicador/abrangencia/valor) | **PASS** | nulos por campo: {'tempo_id': 0, 'localidade_id': 0, 'indicador_id': 0, 'abrangencia_id': 0, 'valor': 0} |
| Consistência de sexo (vitima sempre tem sexo_id; contagem/peso nunca têm) | **PASS** | linhas 'vitima' sem sexo_id: 0 (esperado 0); linhas não-'vitima' com sexo_id: 0 (esperado 0) |
| Cada indicador pertence a exatamente uma família de medida na fact table | **PASS** | nenhuma mistura encontrada |
| Toda linha de dim_indicador tem `unidade` preenchida | **PASS** | 0 linha(s) de dim_indicador sem unidade definida |
| Consistência temporal (meses contínuos por ano, flag is_partial_year correta) | **PASS** | ok |

## 'Não informado' dentro da família aplicável (por evento)

Diferente de 'não aplicável' (estrutural, esperado — ex.: `total` nulo para eventos da família vítima), estes são casos em que o evento pertence à família de medida, mas o valor específico não foi reportado pela fonte para aquela combinação de UF/Município/Mês/Abrangência (e demais dimensões aplicáveis). Essas linhas **não são carregadas** na fact_indicadores (nunca preenchidas com 0) e são quantificadas aqui para transparência.

| Evento | Família | Linhas de grão real | Valores aplicáveis | Não informados | % |
|---|---|---:|---:|---:|---:|
| Apreensão de Cocaína | peso | 1,620 | 1,620 | 127 | 7.84% |
| Apreensão de Maconha | peso | 1,620 | 1,620 | 124 | 7.65% |
| Arma de Fogo Apreendida | contagem | 14,580 | 14,580 | 760 | 5.21% |
| Atendimento pré-hospitalar | contagem | 810 | 810 | 26 | 3.21% |
| Busca e salvamento | contagem | 810 | 810 | 26 | 3.21% |
| Combate a incêndios | contagem | 810 | 810 | 26 | 3.21% |
| Emissão de Alvarás de licença | contagem | 810 | 810 | 39 | 4.81% |
| Estupro | vitima | 810 | 2,430 | 4 | 0.16% |
| Estupro de vulnerável | vitima | 810 | 2,430 | 112 | 4.61% |
| Feminicídio | vitima | 167,910 | 503,730 | 2,714 | 0.54% |
| Furto de veículo | contagem | 1,620 | 1,620 | 810 | 50.00% |
| Homicídio doloso | vitima | 167,910 | 503,730 | 2,703 | 0.54% |
| Lesão corporal seguida de morte | vitima | 167,910 | 503,730 | 205 | 0.04% |
| Mandado de prisão cumprido | contagem | 268,656 | 268,656 | 5,755 | 2.14% |
| Morte de Agente do Estado | vitima | 7,209 | 21,627 | 4,323 | 19.99% |
| Morte no trânsito ou em decorrência dele (exceto homicídio doloso) | vitima | 167,910 | 503,730 | 3,067 | 0.61% |
| Morte por intervenção de Agente do Estado | vitima | 2,376 | 7,128 | 1,957 | 27.46% |
| Mortes a esclarecer (sem indício de crime) | vitima | 167,910 | 503,730 | 19,413 | 3.85% |
| Mortes no trânsito | vitima | 151,416 | 454,248 | 1,110 | 0.24% |
| Pessoa Desaparecida | vitima | 2,430 | 7,290 | 105 | 1.44% |
| Pessoa Localizada | vitima | 2,430 | 7,290 | 120 | 1.65% |
| Realização de vistorias | contagem | 810 | 810 | 51 | 6.30% |
| Roubo a instituição financeira | contagem | 1,620 | 1,620 | 826 | 50.99% |
| Roubo de carga | contagem | 1,620 | 1,620 | 832 | 51.36% |
| Roubo de veículo | contagem | 1,620 | 1,620 | 810 | 50.00% |
| Roubo seguido de morte (latrocínio) | vitima | 167,910 | 503,730 | 835 | 0.17% |
| Suicídio | vitima | 167,910 | 503,730 | 3,402 | 0.68% |
| Suicídio de Agente do Estado | vitima | 7,209 | 21,627 | 4,379 | 20.25% |
| Tentativa de feminicídio | vitima | 167,910 | 503,730 | 7,654 | 1.52% |
| Tentativa de homicídio | vitima | 167,910 | 503,730 | 2,911 | 0.58% |
| Tráfico de drogas | contagem | 1,620 | 1,620 | 0 | 0.00% |