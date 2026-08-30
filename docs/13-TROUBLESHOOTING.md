# 13 — Troubleshooting

> Navegação: [Índice](README.md) · ← [Contribuição](12-CONTRIBUTING.md)

Problemas confirmados durante o desenvolvimento e deploy, com o padrão
**sintoma → causa → diagnóstico → solução**.

---

## A API não inicia

**Sintoma**: `uvicorn src.api.main:app` sai com erro no import.

**Causas possíveis**
- Dependência faltando (`ModuleNotFoundError`).
- `DATABASE_ENGINE` com valor inválido (qualquer coisa diferente de
  `duckdb` cai no modo `postgres`).

**Diagnóstico**
```bash
python -c "import src.api.main"          # mostra o traceback real
echo $DATABASE_ENGINE
```

**Solução**
- Modo produção: `pip install -r requirements-api.txt`.
- Modo dev: `pip install -r requirements.txt`.
- Definir `DATABASE_ENGINE=duckdb` **exatamente** (minúsculas).

---

## `database: "disconnected"` no `/health` (modo DuckDB)

**Sintoma**: `/api/v1/health` retorna 503,
`{"database": "disconnected"}`.

**Causa**: o arquivo `atlas_public.duckdb` não foi encontrado ou não abriu.

**Diagnóstico**
```bash
ls -la data/production/atlas_public.duckdb        # existe?
python -c "import duckdb; duckdb.connect('data/production/atlas_public.duckdb', read_only=True).execute('select 1')"
echo $DUCKDB_PATH
```

**Solução**
- Gerar o arquivo: `python -m src.production.build_dataset`.
- Conferir que ele está versionado (`git ls-files | grep atlas_public.duckdb`).
- Em produção, conferir `DUCKDB_PATH` (default: `data/production/atlas_public.duckdb`,
  relativo à raiz do repo — o Render roda a partir da raiz).

---

## Dataset DuckDB não encontrado no deploy

**Sintoma**: build no Render OK, mas `/health` retorna 503.

**Causa**: o `.duckdb` não entrou no repositório (o `.gitignore` bloqueia
`data/production/*` por padrão).

**Diagnóstico**
```bash
git check-ignore data/production/atlas_public.duckdb   # deve dar exit 1 (NÃO ignorado)
git ls-files | grep atlas_public.duckdb                # deve listar o arquivo
```

**Solução**: o `.gitignore` tem as linhas
`!data/production/atlas_public.duckdb` e
`!data/production/manifest.json`. Se faltarem, adicionar e
`git add -f data/production/atlas_public.duckdb`.

---

## PostgreSQL indisponível

**Sintoma** (modo dev): `/health` 503; testes de integração pulados;
`run_etl` loga `Carga no PostgreSQL falhou`.

**Causa**: contêiner parado ou porta errada.

**Diagnóstico**
```bash
docker ps --format '{{.Names}} {{.Status}}'
docker exec atlas_postgres pg_isready -U atlas -d atlas
```

**Solução**
```bash
docker compose up -d postgres
```
O ETL é *best-effort* quanto ao PostgreSQL — os Parquet continuam sendo
gerados mesmo se a carga falhar.

---

## CORS bloqueando o consumidor

**Sintoma**: no navegador, `Access to fetch ... has been blocked by CORS
policy`. A mesma URL responde 200 via `curl`.

**Causa**: o domínio do consumidor não está em `CORS_ORIGINS`. Em produção,
se a variável não foi definida, o default é `http://localhost:3000,...`.

**Diagnóstico**
```bash
curl -I -H "Origin: https://meu-consumidor.com" \
  https://sentinel-api-sjie.onrender.com/api/v1/health
# procurar o header access-control-allow-origin na resposta
```

**Solução**: no painel do Render, definir
`CORS_ORIGINS=https://meu-consumidor.com` (múltiplos domínios separados por
vírgula, sem espaços supérfluos). **Nunca** `*`. Redeploy.

---

## Consumidor usando `localhost` em produção

**Sintoma**: o app publicado tenta bater em `http://localhost:8000` e falha.

**Causa**: a URL da API está hardcoded ou a variável de ambiente do
consumidor não foi configurada no ambiente de produção dele.

**Diagnóstico**: inspecionar as requisições de rede no navegador — para
onde estão indo.

**Solução**: no projeto consumidor, apontar a base URL para
`https://sentinel-api-sjie.onrender.com/api/v1` no ambiente de produção.
(Este repositório não controla o consumidor.)

---

## Render hibernando / cold start

**Sintoma**: a primeira requisição depois de um tempo demora ~50 s;
depois normaliza.

**Causa**: plano gratuito do Render dorme o serviço após ~15 min sem
tráfego. Somado a isso, a primeira query DuckDB do processo parseia as 26
views (+~0,4 s).

**Solução**: esperado no free tier. Opções: um ping periódico externo para
manter o serviço acordado, ou um plano pago. Não é um bug.

---

## Dados não aparecem / vêm vazios

**Sintoma**: endpoint responde 200 mas `data: []`.

**Causas possíveis**
- Filtro sem correspondência (ex.: `ano=2023` — só há 2024–2026).
- `indicator_id` inexistente → na verdade retorna **404**, não lista vazia.
- No modo DuckDB: dataset desatualizado (build antigo).

**Diagnóstico**
```bash
curl "$BASE/api/v1/metadata"           # confere período e cobertura
curl "$BASE/api/v1/metadata/years"     # [2024,2025,2026]
python -c "import json;print(json.load(open('data/production/manifest.json'))['built_at'])"
```

**Solução**: ajustar o filtro; ou reconstruir o dataset
(`python -m src.production.build_dataset`) e redeployar.

---

## Divergência de valores PostgreSQL × DuckDB

**Sintoma**: `pytest tests/test_production_parity.py` falha.

**Causas possíveis**
- `valor` não foi convertido para `DECIMAL(14,3)` no build (drift de
  `float` no `SUM`).
- Alguma folha de `sql/analytics/` usa sintaxe incompatível com DuckDB.
- Repository usa `CAST(:x AS CHAR(2))` (DuckDB não aceita `CHAR(n)`) — deve
  ser `VARCHAR`.

**Diagnóstico**: o teste que falhou mostra as duas listas de linhas
(`assert p == d`). Comparar.

**Solução**: revisar o cast no `build_dataset.py` (`_load_fact`) ou no
repository. Regenerar o dataset e rodar a paridade de novo.

---

## Porta 8000 (ou 5433) ocupada

**Sintoma**: `[Errno 48] Address already in use` ao subir uvicorn; ou o
`docker compose up` reclama da porta 5433.

**Diagnóstico**
```bash
# Unix
lsof -i :8000
# Windows
netstat -ano | findstr :8000
```

**Solução**: matar o processo, ou usar outra porta
(`uvicorn ... --port 8010`). A porta 5433 (em vez de 5432) já foi escolhida
para evitar conflito com um PostgreSQL nativo — se ela também estiver
ocupada, ajustar `POSTGRES_PORT` no `.env` e no `docker-compose.yml`.

---

## Build do dataset gera arquivo grande (~42 MB) ou lento

**Sintoma**: `atlas_public.duckdb` muito maior que ~17 MB.

**Causa**: a `stg_sinesp` foi materializada no arquivo final e não
compactada (DuckDB não recupera espaço após `DROP TABLE`).

**Solução**: a versão atual do `build_dataset.py` usa a estratégia de **duas
fases** (staging só numa conexão `:memory:`). Se você modificou o builder,
garanta que `stg_sinesp` nunca é criada como tabela no arquivo de saída.

---

## `openpyxl` / leitura do `.xlsx` falha

**Sintoma**: `run_etl` falha na etapa RAW.

**Causas possíveis**
- Arquivo ausente em `data/raw/` (nome exato: `BancoVDE <ano>.xlsx`).
- Aba com nome diferente do ano.
- Coluna esperada faltando (`load_raw` valida as 14 colunas).

**Diagnóstico**: a mensagem de erro diz qual arquivo/coluna.

**Solução**: conferir nome do arquivo, nome da aba (deve ser `"2024"`,
`"2025"`, ...) e o cabeçalho das colunas.
