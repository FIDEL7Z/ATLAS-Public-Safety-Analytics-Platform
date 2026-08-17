# ATLAS — Especificação das Páginas

Blueprint página a página: o que cada visual mostra, de onde vêm os dados, e por que está desenhado assim. Segue a ordem e o escopo definidos na Fase 3. Todas as páginas usam o tema `powerbi/atlas_theme.json` e o cabeçalho fixo "ATLAS — Public Safety Analytics" (ver `docs/POWERBI_DESIGN_SYSTEM.md`).

---

## Página 01 — Executive Overview

**Pergunta que a página responde:** *"Qual é o panorama dos indicadores analisados?"*

### Linha de KPI cards (topo, 5-6 cards, mesma altura)

| Card | Fonte | Formato |
|---|---|---|
| Período Analisado | `MIN('Dim Tempo'[data_referencia])` a `MAX(...)`, formatado "MMM/AAAA" | texto |
| Indicadores Monitorados | `[Total Indicadores]` | 31 |
| UFs Analisadas | `[Total UFs]` | 27 |
| Municípios | `[Total Municípios]` | 5.298 |
| Cobertura 2026 | `[Rótulo Ano Selecionado]` fixado no contexto ano=2026 (visual-level filter) | "DADOS PARCIAIS — JAN a JUN/2026" |

### Bloco "5 famílias" (regra 7 — nunca uma única unidade)

**Cinco cartões lado a lado, cada um com seu próprio título e cor (categórica fixa do design system) — nunca um único gráfico somando os cinco:**

| Bloco | Cor | Medida | Detalhe |
|---|---|---|---|
| VÍTIMAS | azul | `[Total Vítimas]` | + mini-gráfico de linha (sparkline) da evolução mensal |
| OCORRÊNCIAS | laranja | soma filtrada a `tipo_indicador LIKE 'Ocorrência%'` | idem |
| AÇÕES POLICIAIS | água | soma filtrada a `tipo_indicador = 'Ação Policial'` | idem |
| APREENSÕES (unidade) | magenta | soma filtrada a `tipo_indicador = 'Apreensão - Unidade'` | armas apreendidas |
| PESOS (kg) | amarelo | `[Total Peso Apreendido (kg)]` | Cocaína + Maconha |

Cada cartão tem, em texto pequeno abaixo do número, a unidade (`pessoas`, `ocorrências`, `armas`, `kg`) — nunca dois cartões desta linha compartilham eixo/escala.

### Evolução temporal (small multiples)

Gráfico de linha com **small multiples por `grupo_semantico`** (Power BI: campo "Small multiples" = `Dim Indicador[grupo_semantico]`) — 5-6 mini-gráficos lado a lado, cada um com sua própria escala vertical. Nunca um único gráfico de linha somando todos os grupos no mesmo eixo.

### Ranking

Barra horizontal: Top 5 UFs do indicador headline do dashboard (sugestão: "Homicídio doloso", configurável via um parâmetro/bookmark) — usa `[Ranking UF]` + `[Total Valor]`, filtro `TOPN(5, ...)`.

### Distribuição

**Não é um gráfico de pizza somando as 5 famílias.** É uma tabela: `grupo_semantico | Contagem de Indicadores | Contagem de Registros` — uma distribuição por *quantidade*, não por *valor somado*, porque contar linhas é unit-agnostic (uma "ocorrência" e uma "linha de registro" são comparáveis como contagem; kg e pessoas somados não são).

---

## Página 02 — Temporal Analysis

**Slicers (faixa superior, sincronizados):** Indicador (`Dim Indicador[evento]`, seleção única), UF (opcional), Abrangência (opcional).

| Visual | Medidas | Observação |
|---|---|---|
| Linha temporal principal | `[Total Valor]` por `data_referencia` | eixo único, um indicador por vez |
| Rótulo "2026 parcial" | `[Rótulo Ano Selecionado]` | card de texto acima do gráfico, sempre visível quando o ano em contexto for parcial |
| Comparação YoY (colunas agrupadas) | `[Total Período Comparável]` por `ano` | usa o corte de mês dinâmico — nunca Jan-Dez vs Jan-Jun |
| Média móvel | `[Total Valor]` + `[Média Móvel 3M]`, mesma linha temporal | duas séries, mesma unidade — comparável |
| Variação % | `[Variação % MoM]` em colunas, cor por sinal (azul ↑ / vermelho ↓ do par divergente) | nunca rótulo em todo ponto — só nos extremos |

---

## Página 03 — Geographic Analysis

**Slicers:** Indicador (seleção única), Ano, Abrangência.

| Visual | Fonte | Observação |
|---|---|---|
| Ranking de UF (barra horizontal, principal) | `[Ranking UF]` + `[Total Valor]` | visual primário — sempre funciona, não depende de shapefile externo |
| Mapa (opcional/avançado) | `Dim Localidade[uf]` + `[Total Valor]` num Shape Map | requer um TopoJSON de UFs do Brasil não incluído neste repositório — tratar como melhoria opcional, não bloqueante |
| Tabela analítica | UF, Total, `[Participação % UF]`, `[Ranking UF]` | ordenável |
| Evolução da UF selecionada | `[Total Valor]` por `data_referencia`, filtrado pela UF clicada no ranking (cross-filter nativo) | drill-down Brasil → UF → Município via clique |
| Drill-down município | tabela `Dim Localidade[municipio]` + `[Total Valor]`, filtrada pela UF selecionada | usa a mesma relação `Fato Indicadores` → `Dim Localidade` |

**Texto fixo obrigatório na página** (não editável por filtro): *"Valores absolutos — não representam taxa populacional. Este projeto não incorpora dados de população por não ter uma fonte autorizada integrada."*

---

## Página 04 — Indicator Analysis

**Seletor de indicador:** slicer tipo Lista, seleção única, `Dim Indicador[evento]`. Ao lado, um card fixo mostrando `[Unidade Selecionada]` — o usuário sempre vê a unidade do que está olhando.

| Visual | Fonte | Visível quando |
|---|---|---|
| Card "Indicador + Unidade" | `[Indicador Selecionado]`, `[Unidade Selecionada]`, `[Total Valor (Seguro)]` | sempre |
| Evolução temporal | `[Total Valor]` por `data_referencia` | sempre |
| Ranking de UF | `[Ranking UF]` | sempre |
| Distribuição por sexo | `[Participação % Sexo (no indicador)]`, relação com `Dim Sexo` | só indicadores da família vítima — nos demais, o visual fica vazio (sem erro, sem dado a mostrar) |
| Distribuição por faixa etária | relação com `Dim Faixa Etária` | só Pessoa Desaparecida/Localizada |
| Distribuição por agente | relação com `Dim Agente` | só Morte/Suicídio de Agente do Estado |
| Distribuição por arma | relação com `Dim Arma` | só Arma de Fogo Apreendida |

Os 4 últimos visuais **não precisam de lógica condicional para existir** — como as relações são reais (FK nullable no Postgres, replicada como relacionamento no Power BI), um indicador sem faixa etária simplesmente não tem linhas em `Dim Faixa Etária` relacionadas, e o visual mostra "sem dados" naturalmente. Polimento opcional: usar visibilidade condicional (bookmarks) para *esconder* o visual em vez de mostrá-lo vazio — não obrigatório para a página funcionar corretamente.

---

## Página 05 — Analytical Radar

**A página diferencial do ATLAS.** Sem slicer de indicador único obrigatório — z-score é comparável **entre** indicadores de famílias diferentes (é isso que o torna especial: é a única métrica do dashboard que pode legitimamente cruzar unidades, porque compara *desvios padronizados*, não valores brutos).

| Visual | Fonte | Observação |
|---|---|---|
| Tabela "Maiores desvios" | `Indicador \| Mês \| Total \| Média Histórica \| Desvio Padrão \| Z-Score`, ordenada por `ABS([Z-Score])` desc, filtro visual `ABS([Z-Score]) > 2` | cabeçalho da última coluna: **"Anomalia Estatística (Z)"**, nunca "Alerta" |
| Card "Maior desvio do período" | `TOPN(1, ..., ABS([Z-Score]))` — dinâmico, recalcula se os dados mudarem | nunca um texto fixo/hardcoded — deve continuar reproduzível pela camada analítica |
| Top 5 maiores crescimentos | `[Variação % YoY (mesmo mês)]` desc | separado da tabela de quedas |
| Top 5 maiores quedas | `[Variação % YoY (mesmo mês)]` asc | — |

**Regra de linguagem (obrigatória, texto fixo na página):** *"Esta página identifica desvios estatísticos, não causas. Um valor fora do padrão histórico é uma anomalia a investigar — não uma afirmação de crime, causa ou culpa."* Nenhum rótulo desta página usa as palavras "crime", "causa" ou "problema" — apenas "desvio", "anomalia estatística", "comportamento atípico".

---

## Página 06 — Data Quality (auditoria)

**Objetivo:** demonstrar maturidade técnica — esta é a página que evidencia o rigor de todas as fases anteriores.

| Visual | Fonte |
|---|---|
| KPI cards: Linhas RAW/Staging, Linhas Fato, Indicadores, UFs, Municípios, Meses em Anos Parciais | tabela `Qualidade Resumo` |
| Tabela de qualidade por indicador | `Qualidade Não Informado`: evento, familia_medida, linhas_grao_real, valores_aplicaveis, valores_nao_informados, pct_nao_informado, `[Status Qualidade]` (cor condicional pela paleta de status) |
| Texto de cobertura temporal | "Período: Jan/2024 a Jun/2026 · 2026 com 6 de 12 meses (dados parciais)" — vindo de `Qualidade Resumo` |
| Texto de reconciliação ETL | "31/31 indicadores reconciliados (RAW = FACT, Fase 1) · 13/13 testes da camada analítica passando (Fase 2)." — referência a `docs/ETL_RECONCILIATION.md` e à suíte de testes, não recalculado no Power BI |

---

## Regra transversal de todas as páginas

Nenhum visual soma `valor` sem, no mínimo, um filtro implícito de `familia_medida` (via slicer de indicador, via medida pré-filtrada, ou via `[Total Valor (Seguro)]`). Antes de publicar qualquer página nova, perguntar: *"se eu tirar todos os filtros deste visual, o número ainda faz sentido?"* — se a resposta for "não", falta um filtro ou a medida errada foi usada.
