# ATLAS — Fase 0.5: Model Validation

**Objetivo:** validar, com base exclusivamente nos 3 arquivos XLSX (carga integral, sem amostragem), se a hipótese de modelagem dimensional inicialmente proposta está correta — antes de escrever qualquer código de ETL.

**Método:** os arquivos de 2024 e 2025 foram recarregados especificamente para esta fase (o de 2026 já havia sido validado na Fase 0). Todas as afirmações abaixo são verificáveis nos scripts exploratórios que geraram os números — nenhum valor foi estimado ou presumido.

---

## 1. Validação da granularidade declarada

**Hipótese testada:** `UF × Município × Evento × Mês × Abrangência`

**Resultado: a hipótese está INCOMPLETA.**

Testei essa chave reduzida (sem `agente`/`arma`/`faixa_etaria`) contra a chave completa (incluindo os três campos) nas linhas de fora do DF:

| Ano | Duplicatas com chave REDUZIDA (sem agente/arma/faixa) | Duplicatas com chave COMPLETA (com agente/arma/faixa) |
|---|---|---|
| 2024 (excl. DF) | 12.496 | 640 |
| 2025 (excl. DF) | 12.112 | 256 |

A chave reduzida gera **milhares de falsas duplicatas** — porque três indicadores dependem estruturalmente desses campos para serem únicos:
- `Arma de Fogo Apreendida` só é única com `arma` (9 tipos de arma → 9 linhas por UF/Município/Mês).
- `Morte de Agente do Estado` e `Suicídio de Agente do Estado` só são únicas com `agente` (9 tipos de agente).
- `Pessoa Desaparecida` e `Pessoa Localizada` só são únicas com `faixa_etaria` (3 faixas).

**Granularidade real e validada:**

```
UF × Município × Evento × Mês × Abrangência × [Agente] × [Arma] × [Faixa Etária]
```

onde os três últimos campos são **condicionais** — nulos para a maioria dos eventos, mas parte obrigatória da chave para os 5 eventos citados acima. Um modelo dimensional que ignore isso vai colidir linhas legítimas ao agregar.

## 2. Comportamento especial do DF/Brasília — hipótese revisada

A Fase 0 concluiu, com base apenas em 2026, que 100% das duplicatas eram do DF. **Recarregando 2024 e 2025 para confirmar, essa conclusão se mostrou parcialmente incorreta** — e é registrada aqui como correção, não escondida:

| Ano | Duplicatas totais (linha 100% idêntica) | UF = DF | Outras UFs |
|---|---|---|---|
| 2024 | 4.349 | 4.147 (95,4%) | PR: 164 · RJ: 32 · AP: 6 |
| 2025 | 4.489 | 4.423 (98,5%) | GO: 34 · PE: 30 · RN: 2 |
| 2026 | 2.115 | 2.115 (100%) | — |

**Achado revisado:** o fenômeno é **fortemente concentrado no DF, mas não exclusivo dele**. Nos casos fora do DF, a mesma assinatura se repete — linhas com a chave dimensional completa idêntica mas valores de medida (`feminino`/`masculino`/`total_vitima`) diferentes entre si — o que indica o mesmo mecanismo (uma dimensão de origem mais granular do que a exportada), não uma coincidência de exportação. Não há, nos dados, informação suficiente para determinar a causa exata dos casos de PR/RJ/AP/GO/PE/RN (podem ser unidades de reporte específicas — batalhões, delegacias regionais — que não têm coluna própria no export). Isso é declarado como **limitação conhecida, não resolvida**, e não deve ser inventada uma explicação.

**Consequência prática (válida independentemente da causa exata):** a agregação por chave dimensional deve sempre usar `SUM`, nunca `DROP DUPLICATES`, em qualquer UF — não apenas no DF. Tratar isso como regra geral do ETL, não como exceção codificada só para `uf = 'DF'`.

## 3. Relação evento → família de medida → colunas (classificação semântica completa)

Classificação dos 31 eventos, baseada exclusivamente no padrão de colunas preenchidas observado nos dados (idêntico nos 3 anos):

| Evento | Família semântica | Unidade | Colunas utilizadas | Pode ser somado? | Observação |
|---|---|---|---|---|---|
| Feminicídio | Vítima — violência letal | pessoas | feminino, masculino, não_informado, total_vítima | Sim, dentro da família Vítima | Mutuamente exclusivo com Homicídio doloso? Não confirmável nos dados — presumir categorias distintas conforme nomenclatura, mas sem confirmação metodológica externa |
| Tentativa de feminicídio | Vítima — tentativa | pessoas | idem | Sim, mas nunca somar com óbitos consumados | Tentativa ≠ óbito; misturar infla indevidamente indicador de letalidade |
| Homicídio doloso | Vítima — violência letal | pessoas | idem | Sim | — |
| Tentativa de homicídio | Vítima — tentativa | pessoas | idem | Sim, mas nunca somar com óbitos consumados | Mesmo cuidado acima |
| Lesão corporal seguida de morte | Vítima — violência letal | pessoas | idem | Sim | — |
| Roubo seguido de morte (latrocínio) | Vítima — violência letal | pessoas | idem | Sim | — |
| Mortes a esclarecer (sem indício de crime) | Vítima — a esclarecer | pessoas | idem | Cuidado | Não é necessariamente resultado de crime; não somar cegamente em "vítimas de violência intencional" |
| Morte no trânsito ou em decorrência dele (exceto homicídio doloso) | Vítima — trânsito | pessoas | idem | Sim, dentro de trânsito | `abrangencia` = só `Estadual` |
| Mortes no trânsito | Vítima — trânsito | pessoas | idem | Sim, dentro de trânsito | `abrangencia` = só `Polícia Federal`/`PRF` — **complementar**, não duplica o indicador anterior (jurisdições diferentes: rodovia federal vs. demais) |
| Suicídio | Vítima — autoprovocada | pessoas | idem | Não somar com homicídio/latrocínio | Natureza do óbito é oposta (não há agressor) — misturar distorce indicadores de "violência interpessoal" |
| Estupro | Vítima — violência sexual | pessoas | idem | Sim, dentro de sexual | Não é óbito — não somar com indicadores de letalidade |
| Estupro de vulnerável | Vítima — violência sexual | pessoas | idem | Sim, dentro de sexual | Classificação penal distinta de Estupro comum; tratar como subcategoria, não fundir sem rótulo |
| Morte de Agente do Estado | Vítima — agente do Estado (o agente morreu) | pessoas | feminino, masculino, não_informado, total_vítima, agente | Sim, dentro da subfamília | **Não confundir com a linha abaixo** — aqui a vítima é o próprio agente |
| Suicídio de Agente do Estado | Vítima — agente do Estado | pessoas | idem + agente | Sim, dentro da subfamília | Mesmo cuidado |
| Morte por intervenção de Agente do Estado | Vítima — letalidade policial (civil morto por agente) | pessoas | feminino, masculino, não_informado, total_vítima | **Nunca somar** com "Morte de Agente do Estado" | Semanticamente oposto: aqui a vítima é o civil, não o agente — é o indicador de letalidade policial, um dos mais sensíveis do painel |
| Pessoa Desaparecida | Pessoa — desaparecimento | pessoas | feminino, masculino, não_informado, total_vítima, faixa_etária | **Não somar com "Vítima"** | Não é necessariamente resultado de crime; estado em aberto |
| Pessoa Localizada | Pessoa — desaparecimento (resolução) | pessoas | idem | **Nunca somar com indicadores de vítima** | Polaridade oposta — é um desfecho positivo, misturar com óbitos inverteria o sinal do indicador |
| Mandado de prisão cumprido | Ação policial | mandados | total | Sim, dentro da família | Não é ocorrência criminal, é ação de cumprimento judicial |
| Arma de Fogo Apreendida | Apreensão — unidade | armas (unid.) | arma, total | Sim, dentro da família | Unidade = armas; não somar com apreensão de drogas (kg) |
| Furto de veículo | Ocorrência — patrimonial | ocorrências | total | Sim, dentro de patrimonial | Furto ≠ Roubo (ausência/presença de violência) — não fundir sem rótulo |
| Roubo de veículo | Ocorrência — patrimonial | ocorrências | total | Sim, dentro de patrimonial | — |
| Roubo de carga | Ocorrência — patrimonial | ocorrências | total | Sim, dentro de patrimonial | — |
| Roubo a instituição financeira | Ocorrência — patrimonial | ocorrências | total | Sim, dentro de patrimonial | — |
| Tráfico de drogas | Ocorrência — criminal | ocorrências | total | Sim, dentro da família | Contagem de ocorrências, não confundir com peso apreendido (evento diferente) |
| Apreensão de Cocaína | Apreensão — peso | kg | total_peso | Sim, dentro de apreensão-peso | Ver nota de outliers na seção 6 |
| Apreensão de Maconha | Apreensão — peso | kg | total_peso | Sim, dentro de apreensão-peso | Escala ~13x maior que Cocaína; somar as duas dá "kg totais apreendidos" (válido, mesma unidade), mas mistura substâncias com dinâmicas de mercado muito diferentes — rotular claramente |
| Atendimento pré-hospitalar | Serviço — saúde/resgate | atendimentos | total | Sim, dentro de serviços | Não é indicador criminal |
| Busca e salvamento | Serviço — resgate | operações | total | Sim, dentro de serviços | Não é indicador criminal |
| Combate a incêndios | Serviço — bombeiros | ocorrências | total | Sim, dentro de serviços | Não é indicador criminal |
| Emissão de Alvarás de licença | Serviço — administrativo | alvarás | total | Sim, dentro de administrativo | 100% administrativo — maior risco de poluir um "total de ocorrências" se agrupado sem filtro |
| Realização de vistorias | Serviço — administrativo | vistorias | total | Sim, dentro de administrativo | Mesmo cuidado acima |

**Regra geral confirmada nos dados:** cada `evento` popula exclusivamente uma família de colunas — nunca há sobreposição (por exemplo, nenhuma linha tem `total_vitima` e `total_peso` preenchidos simultaneamente, em nenhum dos 3 anos). Isso facilita a modelagem, mas não elimina o risco semântico descrito acima quando indicadores da mesma família de colunas (ex.: `total`) representam coisas tão diferentes quanto "mandado cumprido" e "alvará emitido".

## 4. `feminino/masculino/nao_informado/total_vitima/total/total_peso`: medidas na mesma fact table?

**Risco de dupla contagem identificado:** `total_vitima` é sempre igual a `feminino + masculino + nao_informado` (validado na Fase 0, 0 divergências em ~2M linhas). Se essas 4 colunas forem todas transportadas como medidas independentes para o modelo — inclusive se "despivotadas" para uma dimensão `sexo` — um `SUM()` sem filtro de sexo somaria **o dobro do valor real** (o total mais as 3 parcelas que o compõem).

**Decisão:** `total_vitima` **não deve existir como uma linha/medida independente** no modelo final. Ele deve ser sempre **derivado** — seja em SQL (view/measure calculada) ou em DAX (`SUM` da medida atômica sem filtro de sexo) — nunca armazenado como um quarto valor ao lado de `feminino`/`masculino`/`nao_informado`. As únicas medidas atômicas armazenadas devem ser: `feminino`, `masculino`, `nao_informado` (para a família Vítima/Pessoa), `total` (para Ocorrência/Ação/Serviço) e `total_peso` (para Apreensão-peso).

## 5. Risco de mistura semântica — confirmado

Sim, o risco é real e concreto, não hipotético. Três casos identificados diretamente nos dados (seção 3):

1. **Vítimas vs. Ocorrências vs. Apreensões**: unidades incompatíveis (pessoas / ocorrências / kg / armas). Somar `total_vitima + total + total_peso` produziria um número sem significado.
2. **Polaridade invertida dentro da mesma família de colunas**: `Pessoa Localizada` usa as mesmas colunas que `Homicídio doloso`, mas é um desfecho positivo. Um "Top 10 municípios por total de vítimas" que inclua `Pessoa Localizada` sem filtro correto estaria somando um indicador de sucesso a indicadores de tragédia.
3. **Vítima do agente vs. vítima do Estado**: `Morte de Agente do Estado` (o policial morreu) e `Morte por intervenção de Agente do Estado` (o civil morreu, morto por um policial) usam exatamente as mesmas colunas, mas são análises antagônicas — a segunda é o indicador de letalidade policial, tema sensível que exige rótulo próprio e nunca deve ser confundido com a primeira.

**Conclusão:** o modelo não pode se apoiar apenas em "quais colunas estão preenchidas" para decidir o que é somável — precisa de uma dimensão explícita de classificação semântica (a tabela da seção 3) carregada como atributo do indicador.

## 6. Consistência de `total_peso` entre os eventos que o utilizam

| Evento | Ano | N não-nulo | Mín | Máx | Média | Mediana | P99 |
|---|---|---|---|---|---|---|---|
| Apreensão de Cocaína | 2024 | 602 | 0 | 7.552,93 kg | 355,06 kg | 35,71 kg | 4.186,69 kg |
| Apreensão de Cocaína | 2025 | 594 | 0 | 7.665,83 kg | 336,87 kg | 42,50 kg | 3.220,23 kg |
| Apreensão de Maconha | 2024 | 605 | 0 | 144.340,28 kg | 4.343,06 kg | 133,59 kg | 75.934,66 kg |
| Apreensão de Maconha | 2025 | 594 | 0 | 134.805,76 kg | 4.622,26 kg | 171,44 kg | 54.730,50 kg |

Confirmado: `total_peso` **nunca** aparece fora desses dois eventos (0 linhas em 2024 e 2025), e o campo é sempre não-negativo — comportamento estrutural consistente.

**Porém, a distribuição não é homogênea** — há uma cauda direita extrema, sobretudo em Maconha: a mediana (~130–170 kg) é ordens de grandeza menor que o máximo (~134–144 **toneladas**), e mesmo o P99 (~55–76 toneladas) fica muito abaixo do máximo. Isso indica um pequeno número de apreensões excepcionalmente grandes (megaoperações), que são plausíveis no contexto brasileiro mas que **vão dominar qualquer gráfico de soma simples por UF/mês**. Recomendação para a camada analítica: expor tanto `SUM` quanto `MEDIAN`/`P95` de `total_peso` nos KPIs de apreensão, e sinalizar visualmente os meses/UFs com valores extremos em vez de escondê-los numa média — sem descartar os dados (não há evidência de erro, apenas de assimetria real do fenômeno).

## 7. Comparação de arquiteturas: A vs. B vs. recomendação

### Opção A — `fact_ocorrencias` única (larga, como está hoje)
- ✅ ETL simples (quase 1:1 com a origem); poucas tabelas.
- ❌ 6 colunas de medida majoritariamente nulas (82–99,8%) convivendo na mesma linha.
- ❌ Convida ao erro: nada impede um usuário de arrastar `total_vitima`, `total` e `total_peso` juntos num mesmo visual do Power BI e somá-los — a mistura semântica da seção 5 fica **sem barreira técnica**.
- ❌ Uma medida DAX "genérica" (ex.: "valor do indicador" para um ranking de todos os 31 eventos) exigiria `COALESCE`/`SWITCH` frágil entre 3 colunas.

### Opção B — Fact tables separadas por família (`fact_vitimas`, `fact_ocorrencias_acoes`, `fact_apreensoes`)
- ✅ Isolamento semântico total — impossível somar entre famílias por engano, pois estão em tabelas diferentes.
- ✅ Cada fato tem grão limpo, sem esparsidade de colunas.
- ❌ Multiplica tabelas de fato (3–4), cada uma relacionando-se separadamente com `dim_tempo`/`dim_localidade`/`dim_abrangencia` → modelo mais complexo.
- ❌ Um visual que precise comparar indicadores de famílias diferentes (ex.: "vítimas de homicídio" ao lado de "armas apreendidas" no mesmo território/mês) exige múltiplas fact tables ativas simultaneamente — limitação conhecida do modelo tabular do Power BI (relacionamento ativo único por par de tabelas; comparações cross-fact pedem medidas com `CROSSFILTER` ou uma dimensão-ponte), aumentando a complexidade de DAX exatamente no cenário executivo que o ATLAS mais precisa (Overview).
- ❌ Mais superfície de manutenção: o ETL precisa rotear corretamente cada evento para a fact table certa; um erro de roteamento quebra silenciosamente um KPI.

### Recomendação: Opção C — uma única fact table, em formato longo (unpivoted), com medida genérica + dimensão semântica obrigatória

Nem A nem B como propostas resolvem o problema central (risco de soma incompatível) da melhor forma. A recomendação é uma variante de A, mas transformando as medidas em **uma única coluna `valor`**, com o `evento` carregando, como atributos da dimensão `dim_indicador`, a `familia_semantica` (Vítima, Vítima-Agente do Estado, Pessoa, Ocorrência, Serviço, Apreensão-Peso, Apreensão-Unidade — conforme seção 3) e a `unidade_medida` (pessoas, ocorrências, kg, armas, mandados, etc.). A granularidade de sexo (`feminino`/`masculino`/`nao_informado`) vira uma dimensão `sexo`, não uma medida separada — resolvendo também o risco de dupla contagem da seção 4 (o `total_vitima` deixa de existir fisicamente).

Grão final: `UF × Município × Evento × Mês × Abrangência × [Agente] × [Arma] × [Faixa Etária] × [Sexo]` → uma linha, uma medida (`valor`).

**Justificativa nos critérios pedidos:**

| Critério | Avaliação |
|---|---|
| **Granularidade** | Preserva o grão real validado na seção 1 (incluindo agente/arma/faixa_etária); o unpivot de sexo apenas explicita uma dimensão que já existia implicitamente nas 3 colunas separadas. |
| **Performance** | Aumenta linhas (~2M → ~2,4-2,6M, por causa do unpivot de sexo nas famílias de vítima), mas reduz colunas de 6 esparsas para 1 densa. Em modo importação do Power BI (VertiPaq, compressão colunar), isso é uma troca favorável — menos colunas com alta cardinalidade de nulos comprime pior que uma coluna de valores densos; a diferença de linhas é irrelevante para o motor (testado rotineiramente com dezenas de milhões de linhas). |
| **Clareza semântica** | Máxima: é fisicamente impossível somar "kg" com "pessoas" sem ignorar deliberadamente o filtro de `unidade_medida`/`familia_semantica` — o erro da Opção A deixa de ser "um clique de distância". |
| **Power BI / DAX** | Uma única medida base (`SUM(valor)`) serve para todos os 31 indicadores; a variação é só o contexto de filtro (via `dim_indicador`). Isso é exatamente o padrão que o Power BI foi desenhado para consumir bem (fato único, medidas com `CALCULATE` + filtros de dimensão), e evita o problema de relacionamentos múltiplos da Opção B. |
| **Manutenção** | Novo indicador futuro (ex.: Sinesp adicionar uma 32ª categoria) não exige alteração de schema — só uma nova linha na dimensão `dim_indicador` e novos registros de fato. Nem A (nova coluna) nem B (nova tabela) têm essa propriedade. |
| **Risco de métricas incorretas** | O mais baixo das três opções: o "freio" contra soma incompatível está embutido na própria estrutura da medida (uma coluna, um filtro de família obrigatório para qualquer agregação "genérica"), não depende de disciplina do usuário do relatório nem de lembrar de aplicar `COALESCE` corretamente. |

**Trade-off aceito conscientemente:** a Opção C é ligeiramente mais complexa de construir no ETL do que a Opção A (é necessário um passo explícito de unpivot), mas essa complexidade é paga uma única vez na engenharia — não recorrentemente por cada autor de relatório no Power BI, que é onde o risco realmente mora.

## 8. Regras que a Fase 1 (ETL) deve implementar, decorrentes desta validação

1. Agregações por chave dimensional usam sempre `SUM`, nunca `DROP DUPLICATES` (vale para todas as UFs, não só o DF).
2. A chave de deduplicação/agregação inclui `agente`, `arma` e `faixa_etaria` — nunca omitir esses campos, mesmo que estejam nulos na maior parte das linhas.
3. `total_vitima` não é persistido como coluna/linha de fato — é sempre derivado de `feminino + masculino + nao_informado`.
4. Toda medida carrega, via `dim_indicador`, sua `familia_semantica` e `unidade_medida` — nenhuma medida "solta" sem esse contexto.
5. `Morte de Agente do Estado` e `Morte por intervenção de Agente do Estado` recebem rótulos inequivocamente distintos em qualquer visual (nunca abreviar ambos como "morte de agente").
6. `Pessoa Desaparecida`/`Pessoa Localizada` nunca entram em somatórios de "vítimas de violência letal".
7. KPIs de `total_peso` reportam também mediana/P95, além da soma, dado o achado de outliers da seção 6.

---

*Validação concluída com base em carga integral dos 3 arquivos. Nenhum código de ETL foi escrito nesta fase.*
