# AURA — Setup do Banco de Dados (Supabase)

## Pré-requisitos
- Conta no [supabase.com](https://supabase.com) (gratuita para desenvolvimento)
- Python 3.11+ instalado

---

## Passo 1 — Criar o projeto no Supabase

1. Acesse [supabase.com](https://supabase.com) e faça login
2. Clique em **"New Project"**
3. Configure:
   - **Name:** `aura-dev`
   - **Database Password:** gere uma senha forte e **salve em local seguro**
   - **Region:** `South America (São Paulo)` — menor latência
   - **Plan:** Free (suficiente para desenvolvimento)
4. Clique em **"Create new project"** e aguarde ~2 minutos

---

## Passo 2 — Anotar as credenciais

No painel do Supabase → **Settings → API**:

| Variável | Onde encontrar |
|----------|---------------|
| `SUPABASE_URL` | "Project URL" |
| `SUPABASE_ANON_KEY` | "anon/public" key (usada no Flutter) |
| `SUPABASE_SERVICE_KEY` | "service_role" key (usada no backend Python) |
| `SUPABASE_JWT_SECRET` | Settings → API → JWT Settings → JWT Secret |

> ⚠️ **NUNCA** commite essas chaves no GitHub. Elas ficam apenas no `.env`.

---

## Passo 3 — Executar os arquivos SQL

No painel do Supabase → **SQL Editor → New Query**.

Execute os arquivos **nessa ordem exata**:

### 1. Schema principal
```
01_schema.sql
```
Cria as 18 tabelas, extensões e índices.

### 2. Triggers e funções
```
02_triggers.sql
```
Cria auditoria automática e alertas clínicos automáticos.

### 3. Row Level Security
```
03_rls.sql
```
Aplica políticas de acesso por role (paciente/médico).

**Como verificar:** Vá em **Table Editor** — você deve ver todas as tabelas listadas.

---

## Passo 4 — Validar o schema

```bash
cd supabase/

# Instale as dependências
pip install supabase python-dotenv

# Crie o .env com suas credenciais
echo "SUPABASE_URL=https://SEU_PROJETO.supabase.co" > .env
echo "SUPABASE_SERVICE_KEY=sua_service_key" >> .env

# Execute a validação
python validate_schema.py
```

---

## Estrutura do banco após o setup

```
18 tabelas:
  Identidade:    patients, patient_consents, patient_devices
  Clínico:       patient_diagnoses
  Configuração:  modules, patient_modules, medications, custom_symptoms
  Registros:     mood_records, sleep_records, medication_records,
                 exercise_records, meditation_records, diet_records,
                 symptom_records, crisis_records
  Operacional:   clinical_alerts
  Auditoria:     audit_logs

Triggers ativos:
  - Auditoria automática em todas as tabelas clínicas
  - Alerta automático em crises com intensidade >= 7
  - Alerta automático em crises com ideação suicida
  - Alerta automático em humor <= 2
  - updated_at automático em patients e patient_diagnoses

RLS habilitado em todas as 18 tabelas
```

---

## Erros comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `relation does not exist` | SQL não foi executado | Execute os arquivos em ordem |
| `extension already exists` | Normal em re-execução | Ignore — `IF NOT EXISTS` previne erro |
| `permission denied` | Usando anon key no script | Use a **service_role** key no `.env` |
