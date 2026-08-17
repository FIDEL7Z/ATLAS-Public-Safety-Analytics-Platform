# ATLAS — Data Profile

**Fonte:** Sinesp VDE (Visualizador de Dados Estatísticos) — Ministério da Justiça e Segurança Pública
**Arquivos analisados:** 3 (fornecidos pelo usuário, extraídos do Sinesp VDE)
**Data da análise:** 2026-08-16
**Método:** inspeção direta dos arquivos com `openpyxl` (estrutura) e `pandas` (perfil estatístico completo, carga integral — sem amostragem). Scripts de profiling não foram mantidos no repositório (exploratórios); os resultados brutos estão em `data/quality_reports/profile_raw.json`.

Este documento contém apenas fatos observados nos arquivos. Nenhuma coluna, indicador ou regra foi presumido — onde a fonte não fornece explicação (não há aba de metodologia nos arquivos), isso é declarado explicitamente como limitação.

---

## 1. Arquivos encontrados

| Arquivo | Tamanho | Aba | Linhas (dados) | Colunas |
|---|---|---|---|---|
| `BancoVDE 2024.xlsx` | 30.1 MB | `2024` | 764.788 | 14 |
| `BancoVDE 2025.xlsx` | 27.8 MB | `2025` | 832.285 | 14 |
| `BancoVDE 2026.xlsx` | 13.7 MB | `2026` | 398.985 | 14 |

**Total: 1.996.058 linhas.** Cada arquivo contém **uma única aba**, nomeada com o ano correspondente. Não há aba de metodologia, dicionário de dados ou notas dentro dos arquivos — a análise abaixo foi inteiramente derivada dos valores observados.

Os arquivos foram copiados de `Downloads/` para `data/raw/` (dados brutos, não versionados no Git — ver `.gitignore` a ser criado).

## 2. Estrutura das colunas (idêntica nos 3 arquivos)

| Coluna | Tipo (pandas) | Descrição inferida |
|---|---|---|
| `uf` | string | Sigla da Unidade Federativa (27 valores — 26 estados + DF) |
| `municipio` | string | Nome do município (5.298 valores distintos por ano) |
| `evento` | string | Indicador/tipo de ocorrência (31 categorias — ver seção 4) |
| `data_referencia` | datetime | Mês de referência do dado (granularidade **mensal**, dia sempre `01`) |
| `agente` | string | Tipo de agente do Estado — só preenchido para 2 indicadores específicos (ver seção 4.3) |
| `arma` | string | Tipo de arma apreendida — só preenchido para 1 indicador específico |
| `faixa_etaria` | string | Faixa etária — só preenchida para 2 indicadores específicos |
| `feminino` | float | Nº de vítimas do sexo feminino (indicadores de vítima) |
| `masculino` | float | Nº de vítimas do sexo masculino (indicadores de vítima) |
| `nao_informado` | float | Nº de vítimas com sexo não informado |
| `total_vitima` | float | Total de vítimas = `feminino + masculino + nao_informado` (validado, ver seção 5.4) |
| `total` | float | Contagem de ocorrências para indicadores **não** baseados em vítima (ex.: mandados cumpridos, veículos roubados) |
| `total_peso` | float | Peso (kg, presumido) — usado apenas em apreensões de drogas |
| `abrangencia` | string | Jurisdição do registro: `Estadual`, `Polícia Federal` ou `Polícia Rodoviária Federal` |

**Não presumimos a unidade de `total_peso`** (kg é a convenção usual do Sinesp, mas não há confirmação no arquivo) — isso deve ser tratado como suposição a validar/documentar no dashboard.

## 3. Granularidade

O dataset é uma tabela única em **formato longo**, no nível:

```
UF × Município × Evento × Mês × Abrangência (× Agente / Arma / Faixa Etária, quando aplicável)
```

Ou seja, cada linha é **uma combinação de dimensões**, e não um registro de ocorrência individual (exceto pelo caso do DF — ver seção 5.5). As diferentes famílias de indicadores usam colunas de medida diferentes (ver matriz na seção 4).

## 4. Indicadores (`evento`) e suas colunas de medida

Os 31 valores de `evento` são **idênticos nos três anos**. Cada indicador usa exclusivamente uma família de colunas de medida — nunca mais de uma:

### 4.1 — Indicadores de vítima (`feminino`, `masculino`, `nao_informado`, `total_vitima`)
Feminicídio, Tentativa de feminicídio, Homicídio doloso, Tentativa de homicídio, Lesão corporal seguida de morte, Latrocínio (Roubo seguido de morte), Mortes a esclarecer (sem indício de crime), Morte no trânsito ou em decorrência dele (exceto homicídio doloso), Mortes no trânsito, Suicídio, Estupro, Estupro de vulnerável, Pessoa Desaparecida\*, Pessoa Localizada\*, Morte de Agente do Estado\*\*, Suicídio de Agente do Estado\*\*, Morte por intervenção de Agente do Estado.

\* também preenchem `faixa_etaria`. \*\* também preenchem `agente`.

### 4.2 — Indicadores de contagem (`total`)
Mandado de prisão cumprido, Arma de Fogo Apreendida (também preenche `arma`), Furto de veículo, Roubo de veículo, Roubo de carga, Roubo a instituição financeira, Tráfico de drogas, Atendimento pré-hospitalar, Busca e salvamento, Combate a incêndios, Emissão de Alvarás de licença, Realização de vistorias.

### 4.3 — Indicadores de peso (`total_peso`)
Apreensão de Cocaína, Apreensão de Maconha.

**Implicação de modelagem:** não é possível somar `total_vitima` e `total` de indicadores diferentes num único "total de ocorrências" sem contextualizar — são grandezas de natureza distinta (vítimas vs. ações policiais vs. quilos apreendidos). O modelo dimensional (fato) deve tratar isso via uma dimensão `Indicador` com atributo de "família de medida", e os KPIs executivos devem ser calculados por família, não por soma cega de todas as linhas.

## 5. Qualidade dos dados

### 5.1 — Completude das colunas-chave
`uf`, `municipio`, `evento`, `data_referencia` e `abrangencia` **não têm nenhum valor nulo** em nenhum dos 3 arquivos. As 27 UFs estão presentes em todos os anos (26 estados + DF — cobertura nacional completa).

### 5.2 — Nulos nas colunas de medida (estruturais, não aleatórios)
| Coluna | 2024 | 2025 | 2026 |
|---|---|---|---|
| `agente` | 99,2% | 99,3% | 99,3% |
| `arma` | 99,2% | 99,3% | 99,3% |
| `faixa_etaria` | 99,7% | 99,8% | 99,8% |
| `feminino`/`masculino`/`nao_informado` | ~11–20% | ~19–20%¹ | ~20% |
| `total_vitima` | 10,4% | 17,7% | 18,4% |
| `total` | 90,3% | 82,9% | 82,2% |
| `total_peso` | 99,8% | 99,9% | 99,9% |

¹ leve variação entre as três colunas de sexo.

Esses nulos **não são um problema de qualidade** — são estruturais: cada linha só preenche a família de colunas correspondente ao seu `evento` (seção 4). Por exemplo, `total` é nulo em ~82–90% das linhas porque só se aplica a 12 dos 31 indicadores. **Tratar como "dado ausente" seria um erro de interpretação; o ETL deve tratar isso como "não aplicável".**

### 5.3 — Sem valores negativos
Nenhuma das 6 colunas numéricas (`feminino`, `masculino`, `nao_informado`, `total_vitima`, `total`, `total_peso`) tem valor negativo em nenhum ano — bom indício de qualidade na exportação de origem.

### 5.4 — Consistência interna validada
`total_vitima = feminino + masculino + nao_informado` foi conferido linha a linha nos 3 arquivos: **0 divergências** em ~2 milhões de linhas. A soma das colunas de sexo é sempre igual ao total de vítima declarado.

### 5.5 — Duplicatas (achado metodológico relevante)

Existem linhas totalmente duplicadas (todas as 14 colunas idênticas):

| Ano | Linhas duplicadas (completas) | Grupos duplicados por chave dimensional* |
|---|---|---|
| 2024 | 4.349 | 5.108 |
| 2025 | 4.489 | 5.024 |
| 2026 | 2.115 | 2.277 |

\* chave = `uf, municipio, evento, data_referencia, agente, arma, faixa_etaria, abrangencia` (sem as colunas de medida).

**Investigação (feita sobre 2026, arquivo mais rápido de carregar):** 100% das linhas duplicadas pertencem a `UF = DF, municipio = BRASÍLIA`. Nenhum outro estado tem uma única linha duplicada. Além disso, dentro dos grupos com a mesma chave dimensional, os valores de `feminino`/`masculino`/`total_vitima` **frequentemente divergem** (ex.: um grupo tem linhas com `feminino=0` e `feminino=1` para o mesmo mês/evento) — ou seja, essas não são duplicatas de exportação, e sim **registros distintos que a fonte não conseguiu distinguir com as colunas disponíveis**.

Hipótese mais provável: o Distrito Federal não é dividido em municípios (é uma unidade federativa única, subdividida em Regiões Administrativas), e a fonte aparentemente reporta em um nível mais granular que os demais estados (possivelmente por Região Administrativa ou por unidade da PMDF/PCDF), mas o campo `municipio` sempre mostra `"BRASÍLIA"` (ou `"NÃO INFORMADO"`) para o DF, colapsando essa dimensão extra que não foi exportada.

**Consequência prática para o ETL:** ao agregar por `uf/município/evento/mês`, os valores devem ser **somados (`SUM`)**, nunca deduplicados com `DROP DUPLICATES`. Remover as duplicatas do DF subcontaria a criminalidade da capital federal — em alguns meses, a mesma chave se repete até 33–66 vezes, todas representando ocorrências reais e distintas. Esse comportamento é documentado aqui e será tratado explicitamente na camada de transformação (`src/transformation`), com teste de regressão dedicado (soma pré/pós-agregação por UF deve bater).

### 5.6 — Cobertura de municípios
5.298 municípios distintos por ano (idêntico nos 3 anos, mesma contagem). O Brasil tem 5.570 municípios oficiais (IBGE). **Não presumimos o motivo da diferença** (272 municípios) — pode ser porque nem todo município teve ao menos uma ocorrência registrada em algum indicador no período, ou porque a fonte tem cobertura parcial para certos municípios pequenos. Isso não foi verificado contra uma lista oficial do IBGE (fora do escopo desta etapa) e deve ser tratado como limitação conhecida, não como erro.

### 5.7 — Encoding
Ao inspecionar os arquivos com `openpyxl` em modo bruto, nomes como `"ACREL�NDIA"` e `"Feminic�dio"` apareciam corrompidos — mas isso era um artefato do terminal (codepage do console Windows), **não um problema real nos dados**. Ao carregar com `pandas.read_excel` (engine `openpyxl`) e gravar em UTF-8, os acentos aparecem corretamente (`ACRELÂNDIA`, `Feminicídio`). Nenhuma correção de encoding é necessária no ETL — apenas garantir que toda a pipeline (Python → PostgreSQL → Power BI) use UTF-8 de ponta a ponta.

## 6. Cobertura temporal

| Ano | Meses presentes | Status |
|---|---|---|
| 2024 | Jan–Dez (12 meses) | **Completo** |
| 2025 | Jan–Dez (12 meses) | **Completo** |
| 2026 | Jan–Jun (6 meses) | **PARCIAL** — consistente com a data de hoje (2026-08-16) e o atraso natural de consolidação de dados do Sinesp |

**Regra a aplicar em todo o projeto:** 2026 deve ser rotulado como "Dados Parciais" em qualquer visual comparativo e nunca comparado diretamente (ano completo vs. ano completo) sem normalização (ex.: comparar Jan–Jun/2026 contra Jan–Jun/2025, não contra o total anual de 2025).

## 7. Categorias por dimensão

- **UF (27):** AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR, RJ, RN, RO, RR, RS, SC, SE, SP, TO — idêntico nos 3 anos.
- **Abrangência (3):** `Estadual`, `Polícia Federal`, `Polícia Rodoviária Federal`.
- **Agente do Estado (9, só para 2 indicadores):** Agente de Trânsito, Bombeiro Militar, Guarda Municipal, PF, PRF, Polícia Civil, Polícia Militar, Polícia Penal, Profissionais de Perícia.
- **Arma (9, só para "Arma de Fogo Apreendida"):** Carabina, Espingarda, Fuzil, Metralhadora, Outra, Pistola, Revólver, Rifle, Submetralhadora.
- **Faixa etária (3, só para Pessoa Desaparecida/Localizada):** Maior de Idade, Menor de Idade, Idade Não Informada.

Não existe coluna de **Região** (Norte/Nordeste/etc.) nos arquivos — será derivada em uma dimensão de UF no data warehouse usando o mapeamento padrão IBGE de UF→Região (5 regiões, 27 UFs), já que essa é uma classificação oficial e estável, não um dado a inventar.

## 8. Diferenças entre os 3 arquivos

Nenhuma diferença estrutural: mesmas 14 colunas, mesmos tipos, mesmo conjunto de 27 UFs e 31 eventos nos 3 anos. As únicas diferenças são de **volume** (número de linhas, proporcional ao número de meses) e o fato de 2026 estar incompleto.

## 9. Notas metodológicas

Os arquivos **não contêm** nenhuma aba, célula ou nota com metodologia oficial do Sinesp VDE. Todas as inferências acima (significado de `total` vs `total_vitima`, unidade de `total_peso`, associação evento↔coluna de medida) foram derivadas exclusivamente da observação dos dados, não de documentação oficial. Isso será declarado como premissa assumida em `docs/METHODOLOGY.md`, com recomendação de validação cruzada com a documentação pública do Sinesp VDE quando possível.

## 10. Resumo dos problemas de qualidade identificados

| # | Problema | Severidade | Tratamento no ETL |
|---|---|---|---|
| 1 | Duplicatas de chave no DF (não são exportação, são granularidade perdida) | **Alto** — afeta corretude dos totais do DF se tratado incorretamente | Agregar com `SUM`, nunca `DROP DUPLICATES` |
| 2 | Nulos estruturais em `agente`/`arma`/`faixa_etaria`/`total`/`total_peso` | Baixo (esperado) | Modelar como "não aplicável ao indicador", não como dado ausente |
| 3 | 2026 incompleto (6/12 meses) | Médio | Rotular como "Dados Parciais"; nunca comparar ano completo vs. parcial sem normalização |
| 4 | Cobertura de município (5.298 de 5.570 IBGE) | Baixo — não verificado a fundo | Documentar como limitação conhecida |
| 5 | Sem metodologia oficial embutida nos arquivos | Médio | Premissas documentadas em `METHODOLOGY.md`, com recomendação de checagem cruzada externa |

---

*Relatório gerado a partir da carga integral dos 3 arquivos (sem amostragem). Estatísticas detalhadas por coluna/ano em `data/quality_reports/profile_raw.json`.*
