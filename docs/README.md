# Documentação — ATLAS Public Safety Analytics Platform

Documentação técnica e arquitetural oficial do ATLAS. Todos os números aqui
foram verificados diretamente contra o código, o banco e os testes
(auditoria de 2026-08-30) — não contra documentação anterior.

## Trilha de leitura

| # | Documento | Para quem |
|---|---|---|
| 01 | [Visão do produto](01-PRODUCT_OVERVIEW.md) | Todos — inclusive não técnicos |
| 02 | [Arquitetura](02-ARCHITECTURE.md) | Arquitetos, engenheiros |
| 03 | [Arquitetura de dados](03-DATA_ARCHITECTURE.md) | Data / Analytics Engineers |
| 04 | [Pipeline ETL](04-ETL_PIPELINE.md) | Data Engineers |
| 05 | [Banco de dados](05-DATABASE.md) | Data Engineers, Backend |
| 06 | [Referência da API](06-API_REFERENCE.md) | Backend, consumidores da API |
| 07 | [Produção (PostgreSQL × DuckDB)](07-PRODUCTION.md) | Backend, DevOps |
| 08 | [Deploy](08-DEPLOYMENT.md) | DevOps |
| 09 | [Testes e qualidade](09-TESTING.md) | Todos os engenheiros |
| 10 | [Runbook — atualização de dados](10-DATA_REFRESH.md) | Operação |
| 11 | [Variáveis de ambiente](11-ENVIRONMENT_VARIABLES.md) | Backend, DevOps |
| 12 | [Guia de contribuição / setup local](12-CONTRIBUTING.md) | Novos desenvolvedores |
| 13 | [Troubleshooting](13-TROUBLESHOOTING.md) | Operação, suporte |

## Referências técnicas detalhadas (por fase de construção)

Os documentos abaixo foram escritos durante a construção do projeto e
permanecem válidos como aprofundamento. A trilha 01–13 acima é a fonte
canônica; estes são o "como chegamos aqui".

| Documento | Conteúdo |
|---|---|
| [DATA_PROFILE.md](DATA_PROFILE.md) | Perfil bruto dos 3 arquivos-fonte (Fase 0) |
| [MODEL_VALIDATION.md](MODEL_VALIDATION.md) | Validação do grão real antes do ETL (Fase 0.5) |
| [METHODOLOGY.md](METHODOLOGY.md) | Como cada camada do ETL transforma os dados (Fase 1) |
| [ETL_RECONCILIATION.md](ETL_RECONCILIATION.md) | RAW × STAGING × FACT, evento a evento (gerado pelo ETL) |
| [ANALYTICS_MODEL.md](ANALYTICS_MODEL.md) | Catálogo das views, métricas e performance (Fase 2) |
| [API.md](API.md) | Contrato original da API (Fase 5) — ver 06 para a versão atual |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Arquitetura da Fase 5 — ver 02 para a versão atual |
| [PRODUCTION_ARCHITECTURE.md](PRODUCTION_ARCHITECTURE.md) | Camada DuckDB de produção (Fase 6/7) |
| [POWERBI_*.md](.) | Modelo semântico, medidas DAX e páginas do dashboard Power BI |

## Estado do projeto (verificado)

- **Pipeline de dados**: completo. 5.291.040 linhas na fact table, 31/31
  eventos reconciliados (RAW = FACT).
- **Camada analítica**: 31 views SQL no PostgreSQL.
- **API REST**: FastAPI, somente leitura, 17 endpoints `GET`, 89 testes
  automatizados passando.
- **Produção**: dataset DuckDB de 17 MB (`data/production/atlas_public.duckdb`),
  API rodável sem PostgreSQL, `render.yaml` pronto para deploy gratuito.
- **Power BI**: modelo semântico e medidas especificados; `.pbix` não versionado.
