# Sentinel.io — Guia de Atualização

Como atualizar o dashboard quando novos dados do Sinesp VDE chegarem (ex.: um novo `BancoVDE 2027.xlsx`, ou 2026 se tornar um ano completo).

## Fluxo completo (dados novos)

1. Colocar o novo arquivo em `data/raw/` (não sobrescrever os existentes).
2. Adicionar o ano em `src/config.py` → `RAW_FILES`.
3. Rodar o ETL completo: `python -m src.run_etl` (Fase 1 — recarrega staging + fact do zero, valida reconciliação, recarrega o PostgreSQL).
4. Reaplicar a camada analítica: `python -m src.analytics.build_views` (Fase 2/3 — recria as views; idempotente, sempre seguro rodar de novo).
5. No Power BI Desktop, abrir `powerbi/Sentinel.pbix` → **Página Inicial → Atualizar**. Como o modelo é Import, isso relê todas as tabelas do zero a partir do Postgres já atualizado.
6. Conferir o card "Cobertura 2026" (ou do novo ano) na Executive Overview — se o ano que antes era parcial virou completo, a flag `is_partial_year` já vem correta do Postgres (calculada automaticamente por `dimensions.py`, nunca hardcoded) — nenhuma medida DAX precisa mudar.
7. Rodar a suíte de testes (`pytest`) para confirmar que nada quebrou — 31 testes da Fase 1/2 + testes da Fase 3, se adicionados.

## Atualização agendada (Power BI Service, opcional)

Se o `.pbix` for publicado no Power BI Service, configurar um **gateway de dados local** (Postgres não é uma fonte nativa da nuvem) apontando para o `localhost:5433` da máquina onde o Docker roda, e agendar a atualização (Configurações do Conjunto de Dados → Atualização Agendada). Fora do escopo deste projeto de portfólio (roda localmente), mas documentado para referência.

## O que NUNCA precisa ser refeito manualmente

- Classificação de indicador (`grupo_semantico`, `familia_medida`, `unidade`) — vem de `analytics.vw_dim_indicador`, correta automaticamente para qualquer indicador já mapeado em `src/transformation/reference_data.py`.
- Flag de ano parcial — recalculada a cada rodada do ETL a partir dos meses realmente presentes na fonte.
- Relacionamentos do modelo — não mudam a menos que uma nova dimensão seja adicionada.

## O que exige atenção manual

- Um **evento novo** que não existir em `reference_data.INDICADOR_CLASSIFICATION` faz o ETL **falhar explicitamente** (por design — Fase 0.5/1: nunca classificar um indicador desconhecido automaticamente). Nesse caso: classificar o novo evento em `reference_data.py` (família de medida, unidade, tipo de indicador — baseado em observação real dos dados, nunca em suposição) antes de rodar o ETL de novo.
