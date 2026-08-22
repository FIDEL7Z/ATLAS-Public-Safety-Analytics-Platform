# Sentinel.io — Guia de Construção do Dashboard

Passo a passo para montar o `.pbix` a partir do que já está pronto (PostgreSQL + views + tema + medidas). Estimativa: 2-4 horas para quem já conhece Power BI, seguindo este roteiro.

## Pré-requisitos

1. `docker compose up -d` rodando (verificar: `docker ps` deve mostrar `atlas_postgres (healthy)` na porta 5433).
2. Power BI Desktop instalado.
3. Driver Npgsql/PostgreSQL do Power BI — normalmente já vem com o Power BI Desktop moderno; se pedir, instalar o "Npgsql" via o próprio prompt do conector.

## Passo 1 — Conectar e importar

1. **Obter Dados → PostgreSQL database.**
2. Servidor: `localhost:5433` · Banco de dados: `atlas`.
3. Modo de conectividade de dados: **Importar** (não DirectQuery — ver `docs/POWERBI_MODEL.md` seção 2 para a justificativa).
4. Autenticação: usuário/senha do `.env` local (`POSTGRES_USER=atlas`, `POSTGRES_PASSWORD` conforme configurado).
5. No Navegador, marcar exatamente as tabelas da lista de `docs/POWERBI_MODEL.md` seção 3 — **nenhuma outra**.
6. Em `fact_indicadores`: antes de carregar, abrir **Transformar Dados** e remover a coluna `fact_id` (Editor poderá query-fold isso direto no Postgres — melhor performance de import).
7. Carregar.

## Passo 2 — Renomear para os nomes do modelo semântico

No painel de Campos, renomear cada tabela conforme a coluna "Tabela Power BI" de `docs/POWERBI_MODEL.md` seção 3 (ex.: `fact_indicadores` → `Fato Indicadores`, `vw_dim_indicador` → `Dim Indicador`). Nomes em português, com espaço, batem com as fórmulas DAX do catálogo — copiar exatamente.

## Passo 3 — Relacionamentos

1. **Modelagem → Gerenciar relacionamentos.** Se o auto-detect já criou alguma relação, conferir uma por uma contra a tabela da seção 4 de `docs/POWERBI_MODEL.md` — apagar qualquer relação que não esteja na lista.
2. Criar manualmente as que faltarem: sempre 1 (dimensão) para * (Fato Indicadores), direção do filtro **única** (Dim → Fato).
3. Clicar em `Dim Tempo` → aba **Ferramentas de Tabela** → **Marcar como Tabela de Data** → coluna `data_referencia`.

## Passo 4 — Tema visual

**Exibir → Temas → Procurar temas** → selecionar `powerbi/atlas_theme.json`.

## Passo 5 — Medidas DAX

Em `Fato Indicadores`, criar as medidas de `powerbi/measures.dax`, **na ordem em que aparecem no arquivo** (medidas de baixo reusam as de cima). Organizar em pastas de exibição (clique direito na medida → Pasta de exibição): `01 Core Metrics`, `02 Temporal`, `03 Ranking`, `04 Participation`, `05 Statistical`, `06 Data Quality` — facilita achar cada uma no painel de campos depois.

## Passo 6 — Páginas

Seguir `docs/POWERBI_PAGES.md` uma página por vez, nesta ordem: 01 Executive Overview → 02 Temporal Analysis → 03 Geographic Analysis → 04 Indicator Analysis → 05 Analytical Radar → 06 Data Quality. Nomear as páginas exatamente assim (aparecem na navegação).

Navegação entre páginas: usar os **botões de navegação de página** nativos do Power BI (Inserir → Botões → Navegador de páginas) no cabeçalho, visível em todas as páginas via a opção "Aplicar a todas as páginas".

## Passo 7 — Slicers sincronizados

Para o slicer de Indicador (usado nas páginas 02 e 04) e o slicer de Ano/UF (usado em várias páginas): **Exibir → Sincronizar Slicers** — sincronizar entre as páginas que compartilham o mesmo filtro, para que a seleção persista ao navegar.

## Passo 8 — Validar

Seguir `docs/POWERBI_VALIDATION.md` — conferir cada linha da tabela de validação contra o que o Power BI mostra, preencher a coluna "Power BI" e o status PASS/FAIL.

## Passo 9 — Salvar

Salvar como `powerbi/Sentinel.pbix` (fora do controle de versão do Git por padrão — arquivos `.pbix` são binários grandes; se quiser versionar, considerar o formato **Power BI Project (.pbip)**, que salva o modelo/relatório como texto).
