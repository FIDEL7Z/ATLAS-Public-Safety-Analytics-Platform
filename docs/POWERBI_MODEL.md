# Sentinel.io — Modelo Semântico Power BI

## 1. Princípio de divisão de responsabilidade

| Camada | Responsável por |
|---|---|
| **PostgreSQL** (Fases 1-2) | transformação, agregação de grão, classificação estrutural (`familia_medida`, `unidade`, `grupo_semantico`), regras de negócio estáveis (nullable FKs = "não aplicável", grão real validado) |
| **Power BI / DAX** (Fase 3) | métricas interativas (totais, variações, participação, ranking, estatística), filtros, comparação, apresentação |

O Power BI **não recalcula** `grupo_semantico` nem reagrega o grão real — ele importa o resultado já correto do Postgres e constrói tudo o que precisa reagir a cliques/filtros em cima disso.

## 2. Conexão

| Parâmetro | Valor |
|---|---|
| Tipo de conector | PostgreSQL database (nativo do Power BI Desktop) |
| Servidor | `localhost:5433` (ou o host onde o container `atlas_postgres` estiver publicado — porta 5433, não 5432, ver `docker-compose.yml`) |
| Banco de dados | `atlas` |
| Schema principal | `public` (fact/dimensões) + `analytics` (duas views de apoio à qualidade) |
| Modo de conectividade | **Import** (decisão herdada da Fase 2 — ver `docs/ANALYTICS_MODEL.md` seção 7: o dataset é atualizado em lote, não em tempo real, e o Postgres não precisa atender consultas interativas por clique) |
| Credenciais | usuário/senha do `.env` local (`POSTGRES_USER`/`POSTGRES_PASSWORD`) — **nunca commitadas**; ao conectar, o Power BI pede as credenciais uma vez e as armazena localmente (Windows Credential Manager), fora do arquivo `.pbix` |

Pré-requisito: `docker compose up -d` rodando (ver `README.md`).

## 3. Tabelas importadas (o que — e o porquê de não ser mais que isso)

Um único esquema estrela, nada de "galáxia" de views pré-agregadas em grãos diferentes — evita relacionamentos ambíguos entre tabelas fato de granularidades diferentes.

| Tabela Power BI | Origem | Linhas | Papel |
|---|---|---:|---|
| **Fato Indicadores** | `fact_indicadores` (remover a coluna `fact_id`, não usada em nenhuma medida — regra 16) | 5.291.040 | fato único, grão validado na Fase 0.5 |
| Dim Tempo | `dim_tempo` | 30 | marcada como **Date Table** (coluna `data_referencia`) para habilitar time intelligence |
| Dim Localidade | `dim_localidade` | 5.597 | UF, Município, Região |
| Dim Indicador | `analytics.vw_dim_indicador` (não `dim_indicador` puro — já traz `grupo_semantico`) | 31 | evento, família, unidade, grupo semântico |
| Dim Abrangência | `dim_abrangencia` | 3 | Estadual / PF / PRF |
| Dim Agente | `dim_agente` | 9 | só relevante p/ 2 indicadores |
| Dim Arma | `dim_arma` | 9 | só relevante p/ 1 indicador |
| Dim Faixa Etária | `dim_faixa_etaria` | 3 | só relevante p/ 2 indicadores |
| Dim Sexo | `dim_sexo` | 3 | só relevante p/ família vítima |
| Qualidade Não Informado | `analytics.vw_qualidade_nao_informado` | 31 | só para a página Data Quality |
| Qualidade Resumo | `analytics.vw_qualidade_resumo` | 1 | KPI cards da página Data Quality |

**Views analíticas da Fase 2 (`vw_nacional`, `vw_uf`, `vw_evolucao_temporal`, `vw_pesos_percentis`, `vw_desvio_media_historica`, rankings etc.) não são importadas.** Elas continuam existindo no Postgres como a camada de validação/auditoria SQL (usada nos testes automatizados e nas consultas de reconciliação da seção de Validação abaixo) — mas o Power BI recalcula os mesmos números via DAX sobre o esquema estrela, porque isso é o que dá interatividade real (um usuário filtrando por região precisa que ranking/participação/z-score recalculem *ali*, e uma view SQL fixada num grão não faz isso).

## 4. Relacionamentos

Todos **unidirecionais** (dimensão → fato), cardinalidade **um-para-muitos**, exatamente espelhando as FKs já validadas no Postgres — nenhum relacionamento "artificial" foi necessário porque o esquema já chega pronto como estrela.

| De (coluna 1) | Para (coluna muitos) | Cardinalidade | Direção do filtro |
|---|---|---|---|
| Dim Tempo[tempo_id] | Fato Indicadores[tempo_id] | 1:N | única (Dim → Fato) |
| Dim Localidade[localidade_id] | Fato Indicadores[localidade_id] | 1:N | única |
| Dim Indicador[indicador_id] | Fato Indicadores[indicador_id] | 1:N | única |
| Dim Abrangência[abrangencia_id] | Fato Indicadores[abrangencia_id] | 1:N | única |
| Dim Agente[agente_id] | Fato Indicadores[agente_id] | 1:N | única (FK nullable — linhas sem agente aplicável simplesmente não casam com nenhuma linha de Dim Agente, o que é correto) |
| Dim Arma[arma_id] | Fato Indicadores[arma_id] | 1:N | única |
| Dim Faixa Etária[faixa_etaria_id] | Fato Indicadores[faixa_etaria_id] | 1:N | única |
| Dim Sexo[sexo_id] | Fato Indicadores[sexo_id] | 1:N | única |
| Dim Indicador[evento] | Qualidade Não Informado[evento] | 1:N | única |

Nenhum relacionamento bidirecional. Nenhuma tabela fato relaciona diretamente com outra tabela fato. Ao importar, desmarcar a opção "Auto-detect relationships" do Power BI e conferir manualmente contra esta tabela — o auto-detect por nome de coluna pode sugerir relações incorretas (ex.: duas colunas chamadas `ano` em tabelas diferentes sem FK real).

## 5. Por que nenhuma tabela de "ponte" (bridge) foi necessária

Como `Fato Indicadores` é a única tabela fato do modelo, não existe o problema clássico de múltiplas fact tables com dimensões conformadas — todo filtro flui numa única direção, de qualquer dimensão para o único fato. As tabelas `Qualidade Não Informado`/`Qualidade Resumo` são satélites da página de Data Quality e não precisam se relacionar com `Fato Indicadores` (mostram números já agregados do lado do Postgres).

## 6. Colunas explicitamente NÃO importadas (regra 16 — performance)

- `fact_indicadores.fact_id` — chave técnica sem uso em DAX.
- `stg_sinesp` inteira — camada staging não tem papel no dashboard (é insumo do ETL, não da BI).
- `dim_indicador` puro (sem `grupo_semantico`) — substituído por `analytics.vw_dim_indicador`.
