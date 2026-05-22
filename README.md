# AURA Platform - Backend (FastAPI)

API de acompanhamento psiquiatrico ambulatorial para o projeto AURA.

## Status atual

Este backend esta em fase de MVP tecnico. Ja possui autenticacao por JWT do Supabase, rotas de registros clinicos, consentimento LGPD, modulos de acompanhamento e dashboard medico inicial. Ainda nao deve ser considerado pronto para producao sem testes automatizados, revisao de RLS/politicas de banco e validacao de seguranca ponta a ponta.

## Estrutura

```text
aura-platform-backend/
├── app/
│   ├── auth.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── routes/
│   │   ├── consent.py
│   │   ├── dashboard.py
│   │   ├── logs.py
│   │   ├── modules.py
│   │   └── patients.py
│   └── services/
│       └── alert_service.py
├── supabase/
│   ├── 01_schema.sql
│   └── 02_triggers.sql
├── main.py
├── requirements.txt
└── .env.example
```

## Instalar e executar

```bash
git clone https://github.com/edumimessi/aura-platform-backend.git
cd aura-platform-backend
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

A API fica em `http://localhost:8000` e a documentacao Swagger em `http://localhost:8000/docs`.

## Variaveis obrigatorias

```env
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=...
SUPABASE_JWT_SECRET=...
DEBUG=True
```

Nunca exponha `SUPABASE_SERVICE_KEY` no frontend.

## Endpoints principais

- `GET /health`
- `GET /db-check`
- `POST /patients`
- `GET /patients`
- `POST /api/logs/mood`
- `GET /api/logs/mood/{patient_id}`
- `POST /api/logs/crisis`
- `POST /api/modules/sleep`
- `POST /api/modules/exercise`
- `POST /api/modules/meditation`
- `POST /api/modules/diet`
- `POST /api/modules/symptoms`
- `POST /api/modules/medications`
- `GET /api/dashboard/patients`
- `GET /api/dashboard/patients/{patient_id}/summary`
- `GET /api/dashboard/alerts`
- `PUT /api/dashboard/alerts/{alert_id}/resolve`
- `POST /api/consent`
- `GET /api/consent/status`
- `POST /api/consent/revoke`

## Banco de dados

Execute os arquivos em `supabase/` nesta ordem:

1. `01_schema.sql`
2. `02_triggers.sql`

O backend foi ajustado para usar os nomes de coluna do schema atual, como `score`, `duration_minutes`, `source_type` e `is_enabled`.

## Proximos passos tecnicos

- Adicionar politicas RLS versionadas em SQL.
- Criar testes de permissao medico/paciente.
- Criar testes de contrato para cada endpoint.
- Implementar endpoint real de prescricoes/medicamentos.
- Implementar registro de dispositivos ou remover chamada do frontend ate a fase de push.
- Adicionar CI para lint e testes.

## Licenca

MIT
