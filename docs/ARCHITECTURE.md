# ATLAS — Arquitetura Completa

```
data/raw/*.xlsx (Sinesp VDE, intocado)
        │
        ▼  src/ingestion/load_raw.py
   RAW (em memória)
        │
        ▼  src/transformation/staging.py
   STAGING — stg_sinesp (1:1 com RAW, sem total_vitima)
        │
        ▼  src/transformation/fact.py (SUM pelo grão real — nunca DROP DUPLICATES)
   Grão real agregado
        │
        ▼  unpivot (feminino/masculino/nao_informado/total/total_peso → valor)
   FACT — fact_indicadores (formato longo) + 8 dimensões
        │
        ▼  src/validation/{data_quality,reconciliation}.py
   Relatórios de qualidade + reconciliação (31/31 PASS)
        │
        ▼  src/loading/postgres_loader.py (COPY)
   PostgreSQL (Docker, porta 5433)
        │
        ▼  sql/analytics/*.sql (schema `analytics`, 18 views)
   Camada Analítica SQL (rankings, séries temporais, percentis, z-score)
        │
        ▼  Power BI (Import Mode) + DAX (powerbi/measures.dax)
   ATLAS Dashboard — 6 páginas
```

## As 3 fases

| Fase | Entrega | Documento principal |
|---|---|---|
| 1 — ETL | RAW → STAGING → FACT, PostgreSQL carregado, 18 testes | `docs/METHODOLOGY.md`, `docs/ETL_RECONCILIATION.md` |
| 2 — Analytics Layer | Schema `analytics`, 16 views SQL, 13 testes de integração | `docs/ANALYTICS_MODEL.md` |
| 3 — Power BI | Modelo semântico, medidas DAX, 6 páginas, tema visual | `docs/POWERBI_MODEL.md`, `docs/POWERBI_DAX_MEASURES.md`, `docs/POWERBI_PAGES.md` |

## Validações anteriores à Fase 0.5/1 (fundação de tudo)

| Documento | Conteúdo |
|---|---|
| `docs/DATA_PROFILE.md` | Perfil bruto dos 3 arquivos XLSX (Fase 0) |
| `docs/MODEL_VALIDATION.md` | Validação do grão real e da arquitetura de modelagem (Fase 0.5) |

## Stack

Python (pandas/openpyxl para ETL) → PostgreSQL 16 (Docker) → SQL analítico → Power BI/DAX. Nenhuma tecnologia adicional além do que resolve um problema real do projeto (sem Machine Learning, sem fila de mensagens, sem serviço adicional).

## Princípio de divisão de responsabilidade entre camadas

- **Python/pandas**: parsing do XLSX, tipagem, agregação pelo grão real, construção de dimensões e chaves substitutas.
- **PostgreSQL/SQL**: classificação semântica estrutural (`familia_medida`, `unidade`, `grupo_semantico`), views de auditoria/validação, agregações que são caras ou difíceis de reproduzir em DAX (percentis históricos completos).
- **Power BI/DAX**: tudo que precisa reagir a um clique do usuário — filtros, ranking, participação, comparação temporal, z-score no contexto selecionado.

Nenhuma camada duplica o trabalho da outra por padrão — quando duplicou (ex.: `analytics.vw_qualidade_nao_informado` replicando em SQL um cálculo que já existia em Python), foi uma decisão explícita e documentada, com teste de paridade entre as duas implementações (`tests/test_analytics_sql.py`).

## Regras estruturais que atravessam as 3 fases (nunca violadas)

1. Agregação de duplicatas sempre por `SUM`, nunca `DROP DUPLICATES`.
2. `total_vitima` nunca é uma coluna/medida armazenada — sempre `feminino + masculino + nao_informado` derivado.
3. Nenhuma métrica soma indicadores de `familia_medida`/`unidade` diferentes sem um filtro explícito.
4. 2026 é sempre identificável como ano parcial — a flag é calculada a partir dos dados (meses realmente presentes), nunca hardcoded.
5. Outliers nunca são removidos da base — no máximo, uma métrica separada mostra o efeito deles.
6. Nenhuma classificação de indicador é inventada — um evento não mapeado faz o pipeline falhar explicitamente em vez de seguir com uma suposição.
