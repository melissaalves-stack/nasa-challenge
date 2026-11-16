# AstroKatu — Backend

API de **monitoramento longitudinal de saúde comportamental** para missões longas, com
atraso de comunicação com a Terra. O Tamagotchi é a interface; aqui roda o sistema clínico:
baseline individual, regras explicáveis, revisão humana e **privacy-preserving inference**.

> **Apoio à decisão. Não emite diagnóstico.** Toda resposta clínica carrega esse aviso.

## Rodando

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.seed                      # cria admin / clínico / 2 astronautas (senha: demo1234)
uvicorn app.main:app --reload           # docs interativas em http://localhost:8000/docs
pytest -q                               # testes do núcleo + integração da API
```

Variáveis (ver `.env.example`): `DATABASE_URL` (SQLite por padrão; PostgreSQL funciona), `SECRET_KEY`, `CORS_ORIGINS`.

## Arquitetura

```
app/
├── services/            ← NÚCLEO PURO (sem FastAPI/DB): testável isolado
│   ├── privacy.py       whitelist estrita de features do diário
│   ├── baseline.py      baseline adaptativo com travas
│   ├── series.py        linhas brutas → séries diárias
│   ├── rules.py + rules.yaml   motor de regras explicável (sem eval)
│   ├── actions.py       plano de ações: biblioteca curada, sem LLM livre
│   └── engine.py        orquestra séries → baseline → regras
├── services/pipeline.py, timeline.py   ← cola com o banco (alertas, planos, auditoria)
├── routers/             entries · users · clinician · simulate (demo)
├── simulator/           5 cenários sintéticos determinísticos (seed fixa)
└── models.py            SQLAlchemy 2.0 (SQLite/PostgreSQL)
```

Fluxo: `POST /entries/{sleep|diary}` → grava → `run_pipeline` → alertas + plano de ações → fila do clínico.

## Endpoints

| Quem | Rota | O que faz |
|---|---|---|
| todos | `POST /auth/login`, `GET /auth/me` | JWT |
| astronauta | `POST /entries/vitals` | pulseira (pressão, SpO₂, fadiga), em lote |
| astronauta | `POST /entries/sleep` | telemetria diária (sono, tempo de reação, densidade muscular*) |
| astronauta | `POST /entries/diary` | **só features + hash**; texto cru → 422 |
| astronauta | `POST /users/{id}/consent` | consentimento revogável |
| astronauta/clínico | `GET /users/{id}/timeline`, `/action-plan` | séries + baseline; plano atual |
| astronauta | `POST /action-plans/{id}/feedback` | útil / não útil por ação |
| clínico | `GET /clinician/overview`, `/review-queue` | status por astronauta; fila (críticos primeiro) |
| clínico | `GET /clinician/users/{id}/timeline` | séries com banda do baseline |
| clínico | `GET /clinician/alerts/{id}` | explicação completa + evidências + ações |
| clínico | `POST /clinician/alerts/{id}/review`, `/escalate` | decisão humana (auditada) |
| clínico | `GET /clinician/rule-feedback`, `/audit-log` | taxa de falso positivo por regra; quem viu o quê |
| admin | `POST /admin/simulate`, `GET /admin/scenarios`, `POST /admin/reset/{id}` | modo demo |

\* densidade muscular é **proxy sintético**: entra como contexto, nunca como critério de alerta.

## Decisões de segurança (os argumentos do pitch)

- **O texto do diário não existe no backend.** O contrato só tem features; chaves fora da whitelist → 422;
  `topic_tags` usa vocabulário fechado (tag livre seria canal de vazamento); o handler de erro de validação
  **não ecoa** o payload; só `text_hash` + `local_model_version` podem ir para log.
- **Nenhuma regra dispara com um evento isolado.** Regras de tendência exigem vários dias ("3 de 3 noites",
  "4 de 7 dias"...). A noite ruim isolada não alerta.
- **Marcador de ideação nunca gera ação automática.** Vai para alerta `critical` + `review_required` (topo da fila),
  notificação ao clínico e plano com `requires_human`. O mesmo registro nunca gera dois alertas.
- **Baseline não vira "novo normal":** ≥14 amostras boas, exclui dias `high_workload`, exige mudança sustentada
  (≥7 dias) e ≥1 DP, **congela enquanto há alerta ativo ou hit recente**, e guarda histórico.
- **`review_required` só é fechado por humano.** Se as condições normalizam, o alerta recebe
  `conditions_cleared: true`, mas continua na fila. `info`/`watch` fecham sozinhos após 3 dias sem hit.
- **Sem LLM gerando conteúdo clínico:** plano = biblioteca curada + regras determinísticas.
- Clínico só vê astronautas atribuídos; toda leitura vai para `audit_log`; 404 (não 403) para não revelar existência.

## Demo (3 minutos)

1. `POST /admin/simulate {"scenario":"isolated_bad_night"}` → **zero alertas** (mostre isso).
2. `integrated_deterioration` → `watch` e depois `review_required`, com evidências legíveis em `/clinician/alerts/{id}`.
3. `suicidal_marker` → alerta crítico no topo da fila, `auto_action: false`.
4. `recovery` → alertas fecham, baseline intacto.
5. `POST /entries/diary` com campo `text` → 422.

Cenários: `healthy_baseline`, `isolated_bad_night`, `integrated_deterioration`, `suicidal_marker`, `recovery`.
Seed fixa (42) ⇒ resultado reproduzível. Edite `app/services/rules.yaml` para calibrar regras.

## Como gerar a simulação (passo a passo)

### Opção A: pela API (fluxo completo da demo)

**1. Prepare o ambiente e suba o servidor**

```bash
python -m app.seed                 # cria os usuários de demo e imprime os IDs
uvicorn app.main:app --reload
```

Anote o `id` de `astro1@astrokatu.dev` (aparece na saída do `seed`).

**2. Faça login como admin e guarde o token**

```bash
curl -s -X POST localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@astrokatu.dev","password":"demo1234"}'
```

Copie o `access_token` da resposta.

**3. Rode um cenário**

```bash
curl -s -X POST localhost:8000/admin/simulate \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scenario":"integrated_deterioration","user_id":"ID_DO_ASTRO1","seed":42}'
```

A resposta traz `alert_events` (em que dia cada alerta nasceu ou subiu de gravidade) e a lista
de `alerts` com as explicações.

**4. Veja o resultado como clínico**

Faça login com `clinico@astrokatu.dev` e consulte:

- `GET /clinician/review-queue`: fila de revisão (críticos primeiro);
- `GET /clinician/users/{id}/timeline`: séries com a banda do baseline;
- `GET /clinician/alerts/{id}`: evidências e plano de ações de cada alerta.

Dá para fazer tudo isso na interface interativa em `http://localhost:8000/docs` (botão **Authorize**).
O arquivo `requests.http` tem todas as chamadas prontas.

### Parâmetros de `POST /admin/simulate`

| Campo | Padrão | O que faz |
|---|---|---|
| `scenario` | (obrigatório) | um dos 5 cenários da tabela abaixo |
| `user_id` | (obrigatório) | ID de um usuário com papel `astronaut` |
| `seed` | `42` | mesma seed = mesmo resultado; mude para variar o ruído |
| `reset` | `true` | apaga os dados anteriores do astronauta antes de simular |
| `start_date` | termina hoje | data do primeiro dia simulado |

Com `reset: false` e um período que se sobrepõe a dados existentes, os registros antigos conflitam com os novos.
Para limpar um astronauta use `POST /admin/reset/{user_id}`.

### Cenários e resultado esperado

| Cenário | Resultado esperado |
|---|---|
| `healthy_baseline` | nenhum alerta |
| `isolated_bad_night` | nenhum alerta (noite ruim isolada não é tendência) |
| `integrated_deterioration` | `watch` e depois `review_required` |
| `suicidal_marker` | alerta crítico no topo da fila, `auto_action: false` |
| `recovery` | alertas fecham e o baseline continua intacto |

### O que acontece por dentro

1. O gerador cria **20 dias saudáveis** (a fase de baseline) e depois os dias do cenário.
2. Cada dia gera sono, 4 leituras da pulseira e **features** de diário (nunca texto).
3. O dia é gravado e o pipeline roda com a data daquele dia, como se o tempo estivesse passando.
4. O baseline individual é criado ao atingir 14 amostras boas e depois fica congelado enquanto houver alerta.
5. As regras do `rules.yaml` são avaliadas dia a dia. Alertas e planos de ação são criados, promovidos ou fechados.

### Opção B: sem servidor, só em Python

Roda sem FastAPI nem banco, a partir da pasta `backend/`. É um bom jeito de calibrar o `rules.yaml`
antes de mexer na API:

```python
from tests.helpers import run_scenario

records, timeline, baselines = run_scenario("integrated_deterioration", seed=42)
for rec, res in timeline:
    if res.hits:
        print(rec.date, [(h.rule_id, h.severity) for h in res.hits])
```

## Simulação visual (`/demo`)

Página simples, só para apoio visual: abra **http://localhost:8000/demo** (depois do `python -m app.seed`).

1. Escolha o cenário e o astronauta e clique em **Gerar simulação** (chama `POST /admin/simulate`).
2. Use **Reproduzir** ou o controle deslizante para ver os dias passando: gráficos de sono, fadiga, tempo de
   reação e estresse do diário, com a faixa do baseline individual, dias de alta carga e marcas de alerta.
3. O "Tamagotchi" muda de humor conforme a gravidade dos alertas ativos naquele dia.
4. O painel **Privacy-preserving inference** mostra o texto sendo digitado e destruído (ilustrativo) e, com o
   botão 2, envia texto cru de verdade ao backend para mostrar o `422`.

É um arquivo estático (`app/static/demo.html`) que só consome a API existente; nada do backend foi alterado
além de registrar a rota. A página usa as credenciais do seed, então desligue-a em produção com `ENABLE_DEMO_UI=0`.

## Estado dos testes (leia isto)

- `tests/test_core.py` (18 testes: privacidade, baseline, 5 cenários, ações, senha) **foi executado e passa**.
- A camada FastAPI/SQLAlchemy (`routers/`, `models.py`, `pipeline.py`) foi escrita mas **ainda não foi executada**
  (o ambiente em que foi gerada não tinha acesso à rede para instalar as dependências). Passou em checagem
  estática de sintaxe/imports. **Rode `pytest -q` na primeira vez**: `tests/test_api.py` cobre login → simulação →
  fila crítica → revisão → auditoria. Se algo quebrar, é provável que seja detalhe de integração, não de lógica.
- Calibração: em 120 execuções aleatórias de cenários sem risco, 3 geraram um alerta espúrio por ruído
  (detecção dos cenários de risco: 60/60). Com a seed 42 da demo, zero. Ajuste os limiares no YAML.

## Limitações conhecidas / próximos passos

- Hash do diário: SHA-256 de texto curto pode ser atacado por dicionário. No app real use **HMAC com chave
  guardada no dispositivo** (o backend já aceita qualquer hex de 64 chars).
- A IA local que extrai as features (MiniLM + classificador, ou TF-IDF + regressão logística) é do lado do app;
  o simulador gera features sintéticas no mesmo schema. `suicidal_ideation_flag` precisa de validação clínica antes de qualquer uso real.
- `_notify_clinicians` só enfileira no audit log: troque por push/e-mail/webhook.
- Limiares das regras, vocabulário de tópicos e a biblioteca de ações devem ser definidos com profissionais de saúde.
- Produção: Alembic para migrações, rate limiting, rotação de chaves, criptografia em repouso.
- Dados de teste são 100% sintéticos.
