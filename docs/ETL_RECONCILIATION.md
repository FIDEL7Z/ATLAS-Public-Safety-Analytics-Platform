# ATLAS — ETL Reconciliation Report

**Gerado em:** 2026-08-16 19:31:55
**Eventos verificados:** 31 · **PASS:** 31 · **FAIL:** 0

Para cada evento, o valor agregado bruto (RAW — soma direta dos 3 arquivos fonte, sem nenhuma transformação) é comparado com o valor agregado na fact_indicadores (após staging, agregação pelo grão real e unpivot para o formato longo). STAGING é incluído para evidenciar que a camada staging não altera nenhum valor (é sempre idêntico a RAW).

| Evento | Família | RAW | STAGING | FACT | Diferença | Status |
|---|---|---:|---:|---:|---:|---|
| Apreensão de Cocaína | peso | 499,195.813 | 499,195.813 | 499,195.813 | -0.000000 | **PASS** |
| Apreensão de Maconha | peso | 6,454,649.904 | 6,454,649.904 | 6,454,649.904 | 0.000000 | **PASS** |
| Arma de Fogo Apreendida | contagem | 269,714.000 | 269,714.000 | 269,714.000 | 0.000000 | **PASS** |
| Atendimento pré-hospitalar | contagem | 2,566,756.000 | 2,566,756.000 | 2,566,756.000 | 0.000000 | **PASS** |
| Busca e salvamento | contagem | 1,226,268.000 | 1,226,268.000 | 1,226,268.000 | 0.000000 | **PASS** |
| Combate a incêndios | contagem | 811,197.000 | 811,197.000 | 811,197.000 | 0.000000 | **PASS** |
| Emissão de Alvarás de licença | contagem | 4,049,105.000 | 4,049,105.000 | 4,049,105.000 | 0.000000 | **PASS** |
| Estupro | vitima | 55,319.000 | 55,319.000 | 55,319.000 | 0.000000 | **PASS** |
| Estupro de vulnerável | vitima | 158,681.000 | 158,681.000 | 158,681.000 | 0.000000 | **PASS** |
| Feminicídio | vitima | 3,801.000 | 3,801.000 | 3,801.000 | 0.000000 | **PASS** |
| Furto de veículo | contagem | 508,004.000 | 508,004.000 | 508,004.000 | 0.000000 | **PASS** |
| Homicídio doloso | vitima | 80,563.000 | 80,563.000 | 80,563.000 | 0.000000 | **PASS** |
| Lesão corporal seguida de morte | vitima | 1,704.000 | 1,704.000 | 1,704.000 | 0.000000 | **PASS** |
| Mandado de prisão cumprido | contagem | 726,886.000 | 726,886.000 | 726,886.000 | 0.000000 | **PASS** |
| Morte de Agente do Estado | vitima | 441.000 | 441.000 | 441.000 | 0.000000 | **PASS** |
| Morte no trânsito ou em decorrência dele (exceto homicídio doloso) | vitima | 63,444.000 | 63,444.000 | 63,444.000 | 0.000000 | **PASS** |
| Morte por intervenção de Agente do Estado | vitima | 16,094.000 | 16,094.000 | 16,094.000 | 0.000000 | **PASS** |
| Mortes a esclarecer (sem indício de crime) | vitima | 35,721.000 | 35,721.000 | 35,721.000 | 0.000000 | **PASS** |
| Mortes no trânsito | vitima | 13,611.000 | 13,611.000 | 13,611.000 | 0.000000 | **PASS** |
| Pessoa Desaparecida | vitima | 210,605.000 | 210,605.000 | 210,605.000 | 0.000000 | **PASS** |
| Pessoa Localizada | vitima | 142,325.000 | 142,325.000 | 142,325.000 | 0.000000 | **PASS** |
| Realização de vistorias | contagem | 1,792,882.000 | 1,792,882.000 | 1,792,882.000 | 0.000000 | **PASS** |
| Roubo a instituição financeira | contagem | 181.000 | 181.000 | 181.000 | 0.000000 | **PASS** |
| Roubo de carga | contagem | 22,723.000 | 22,723.000 | 22,723.000 | 0.000000 | **PASS** |
| Roubo de veículo | contagem | 273,206.000 | 273,206.000 | 273,206.000 | 0.000000 | **PASS** |
| Roubo seguido de morte (latrocínio) | vitima | 2,083.000 | 2,083.000 | 2,083.000 | 0.000000 | **PASS** |
| Suicídio | vitima | 41,128.000 | 41,128.000 | 41,128.000 | 0.000000 | **PASS** |
| Suicídio de Agente do Estado | vitima | 351.000 | 351.000 | 351.000 | 0.000000 | **PASS** |
| Tentativa de feminicídio | vitima | 10,267.000 | 10,267.000 | 10,267.000 | 0.000000 | **PASS** |
| Tentativa de homicídio | vitima | 87,718.000 | 87,718.000 | 87,718.000 | 0.000000 | **PASS** |
| Tráfico de drogas | contagem | 524,680.000 | 524,680.000 | 524,680.000 | 0.000000 | **PASS** |

## Interpretação

- STAGING == RAW em todos os eventos: esperado, pois a camada staging não agrega nem filtra linhas.
- FACT == RAW (tolerância 1e-6, para acumulação de ponto flutuante em `total_peso`): confirma que a agregação por grão real (SUM) e o unpivot para o formato longo preservam exatamente o total original — nenhum valor foi perdido, duplicado ou inventado durante a transformação.
- Linhas com valor 'não informado' na fonte (aplicável, mas não reportado) são omitidas da fact_indicadores por design (nunca preenchidas com 0) — como o SUM do pandas ignora NaN em ambos os lados da comparação (RAW e FACT), essa omissão não gera diferença na reconciliação. Essas ocorrências são quantificadas separadamente em `data/quality_reports/DATA_QUALITY_REPORT.md`.