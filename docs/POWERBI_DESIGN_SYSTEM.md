# ATLAS — Design System (Power BI)

Identidade visual do dashboard. Paleta derivada e validada segundo a metodologia da skill `dataviz` (checagem de CVD/contraste embutida na ordem dos slots categóricos — ver `references/palette.md` da skill; não foi necessário revalidar porque o ATLAS usa exatamente a ordem padrão já validada para gráficos de barra/linha/pequenos múltiplos, que é o caso de uso do dashboard).

Arquivo pronto para importar: [`powerbi/atlas_theme.json`](../powerbi/atlas_theme.json) — no Power BI Desktop: **Exibir → Temas → Procurar temas**.

## Princípios

- **Hierarquia antes de cor.** Título → KPI → gráfico → detalhe. Nenhum visual compete com outro por atenção na mesma página.
- **Espaço em vez de bordas.** Sem sombra, sem borda em cartão, sem gradiente decorativo. Separação por espaçamento em branco.
- **Uma cor, um significado.** A cor categórica de `grupo_semantico` é fixa em todas as páginas — Vítimas é sempre azul, Ocorrências é sempre laranja, em qualquer visual do dashboard. Nunca uma paleta diferente por página.
- **Sem 3D, sem pizza com mais de 4 fatias, sem medidor (gauge) decorativo.** Se o visual não responde a uma pergunta específica, ele não entra na página.

## Paleta

### Categórica — `grupo_semantico` (ordem fixa, nunca ciclada)

| Grupo | Cor | Hex |
|---|---|---|
| Vítimas | azul | `#2a78d6` |
| Ocorrências | laranja | `#eb6834` |
| Ações Policiais | água | `#1baf7a` |
| Apreensões (Peso) | amarelo | `#eda100` |
| Apreensões (Unidade) | magenta | `#e87ba4` |
| Serviços | verde | `#008300` |

Esta é a ordem validada (não uma escolha estética livre): pares adjacentes têm separação segura para daltonismo em gráficos de barra/linha. **Nunca reordenar** por página — a cor precisa significar a mesma coisa em todo lugar.

### Sequencial — magnitude (rankings, mapas de calor)

Uma única cor (azul), do claro ao escuro. Usada em: ranking de UF (barra condicional), mapa coroplético de UF por indicador.

### Divergente — desvio (página Radar, z-score)

Azul (abaixo da média histórica) ↔ cinza neutro (zero) ↔ vermelho (acima da média histórica). Nunca usar a cor categórica "Vítimas" (azul) aqui com o mesmo significado do desvio — no Radar, azul/vermelho representam **sinal do desvio**, não o grupo semântico; a página Radar não usa cor categórica por grupo, para não colidir os dois sistemas.

### Status — Data Quality

| Papel | Cor | Uso |
|---|---|---|
| Bom | `#0ca30c` | cobertura completa, reconciliação PASS |
| Atenção | `#fab219` | % não informado moderado (ex.: 10-25%) |
| Sério | `#ec835a` | % não informado alto (> 25%) |
| Crítico | `#d03b3b` | qualquer teste de reconciliação FAIL |

Cor de status **nunca aparece sozinha** — sempre com ícone + texto (ex.: "✓ PASS", não só um quadrado verde).

## Tipografia

Segoe UI (padrão do Power BI) em toda a interface — sem fonte decorativa. Números grandes (KPI cards) usam peso Light; títulos usam Semibold; nenhum texto usa a cor de série (texto é sempre tinta primária/secundária, cor identifica apenas a marca do gráfico).

| Elemento | Tamanho | Peso |
|---|---:|---|
| Número de KPI card | 32-45pt | Light |
| Título de página | 20pt | Semibold |
| Título de visual | 14pt | Semibold |
| Rótulo/eixo | 10-11pt | Regular |

## Layout

- Grade de 12 colunas, margens de 24px.
- KPI cards no topo de cada página (altura fixa, nunca mais que 5-6 cards por página — regra "poucos cliques, poucas surpresas").
- Slicers em uma faixa horizontal única no topo (nunca uma coluna lateral de slicers empilhados) — visível em todas as páginas via **bookmark de sincronização** (sync slicers).
- Nenhum gráfico sem título que declare a pergunta que ele responde (ex.: "Quais UFs concentram mais homicídios dolosos em 2025?", não apenas "Homicídio doloso por UF").

## Nome e identidade do produto

Cabeçalho fixo em todas as páginas: **"ATLAS — Public Safety Analytics"** + subtítulo da página atual. Rodapé: *"Dados: Sinesp VDE / Ministério da Justiça e Segurança Pública. ATLAS é um projeto independente de portfólio — não é um produto oficial do Governo Federal."*
