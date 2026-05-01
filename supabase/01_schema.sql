-- ============================================================
-- AURA — Schema v2
-- Banco de dados para monitoramento ambulatorial psiquiátrico
-- Dr. Eduardo D'Angelo Mimessi — CRM 121.217
--
-- INSTRUÇÕES:
-- Execute este arquivo inteiro no SQL Editor do Supabase.
-- Vá em: painel Supabase → SQL Editor → New Query → cole tudo → Run
--
-- ORDEM IMPORTA: as tabelas são criadas em sequência porque
-- umas referenciam as outras (chaves estrangeiras).
-- Não reorganize os blocos.
-- ============================================================


-- ============================================================
-- EXTENSÕES
-- uuid-ossp: gera UUIDs (identificadores únicos universais)
-- btree_gist: necessário para o constraint de diagnóstico
-- ============================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gist";


-- ============================================================
-- BLOCO 1: CAMADA DE IDENTIDADE
-- ============================================================


-- ------------------------------------------------------------
-- PATIENTS
-- Armazena o mínimo operacional de cada paciente.
-- Propositalmente separado de dados clínicos detalhados.
--
-- LGPD (Art. 11): dados de saúde são categoria especial.
-- Dívida técnica documentada: birth_date e gender estão aqui
-- por conveniência do MVP. Em v1.1, migrar para patient_profiles
-- com criptografia por campo.
-- ------------------------------------------------------------
CREATE TABLE patients (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Referência ao usuário no Supabase Auth.
    -- SET NULL: se o auth-user for deletado (ex: paciente pediu exclusão
    -- de conta), o histórico clínico permanece anonimizado.
    auth_user_id    UUID UNIQUE REFERENCES auth.users(id) ON DELETE SET NULL,

    -- Médico responsável. RESTRICT: não permite deletar médico
    -- que tenha pacientes ativos.
    doctor_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,

    -- Mínimo demográfico necessário para relatórios clínicos.
    -- (concessão MVP — documentada acima)
    birth_date      DATE,
    gender          VARCHAR(20) CHECK (gender IN (
                        'male', 'female', 'non_binary', 'prefer_not_to_say'
                    )),

    -- Soft delete: nunca apagamos pacientes, apenas desativamos.
    -- Isso protege o histórico clínico e cumpre o CFM.
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,

    -- Preenchido quando o paciente exerce direito ao esquecimento (LGPD Art. 18).
    -- Quando preenchido: birth_date e gender devem ser zerados via procedure.
    anonymized_at   TIMESTAMPTZ,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE patients IS
    'Identidade mínima do paciente. PII separada de dados clínicos por design (LGPD).';
COMMENT ON COLUMN patients.anonymized_at IS
    'Preenchido ao anonimizar. Acionar procedure fn_anonymize_patient().';


-- ------------------------------------------------------------
-- PATIENT_CONSENTS
-- Rastreabilidade de consentimento exigida pela LGPD.
-- Cada linha é um evento de consentimento (ou revogação).
-- Nunca atualizamos — só inserimos novas linhas.
-- ------------------------------------------------------------
CREATE TABLE patient_consents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

    -- O que está sendo consentido
    consent_type    VARCHAR(50) NOT NULL CHECK (consent_type IN (
                        'data_processing',      -- processamento de dados de saúde
                        'push_notifications',   -- envio de lembretes
                        'doctor_alerts',        -- alertas ao médico
                        'anonymous_research'    -- uso anônimo em pesquisa
                    )),

    granted         BOOLEAN NOT NULL,           -- true = concedido, false = revogado
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Hash SHA-256 do IP — nunca o IP bruto (princípio da minimização)
    ip_hash         TEXT,
    app_version     VARCHAR(20),                -- versão do app no momento do consentimento

    revoked_at      TIMESTAMPTZ                 -- preenchido se o consentimento foi revogado
);

COMMENT ON TABLE patient_consents IS
    'Log imutável de consentimentos. Nunca atualizar — apenas inserir novas linhas.';


-- ------------------------------------------------------------
-- PATIENT_DEVICES
-- FCM tokens para notificações push.
-- Um paciente pode ter múltiplos dispositivos.
-- Separado de patients porque é dado operacional, não clínico.
-- ------------------------------------------------------------
CREATE TABLE patient_devices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,

    fcm_token       TEXT NOT NULL,
    device_name     VARCHAR(100),               -- 'iPhone 15 do Eduardo'
    platform        VARCHAR(10) CHECK (platform IN ('ios', 'android')),

    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    registered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (fcm_token)                          -- token é único por dispositivo
);


-- ============================================================
-- BLOCO 2: CONFIGURAÇÃO CLÍNICA
-- ============================================================


-- ------------------------------------------------------------
-- PATIENT_DIAGNOSES
-- Linha do tempo diagnóstica — não um campo estático.
-- Diagnóstico psiquiátrico é longitudinal: muda, é revisado,
-- tem comorbidades, tem status (suspeito, confirmado, descartado).
-- ------------------------------------------------------------
CREATE TABLE patient_diagnoses (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

    cid_code            VARCHAR(10) NOT NULL,       -- ex: 'F31.1'
    diagnosis_label     VARCHAR(200) NOT NULL,      -- ex: 'Transtorno afetivo bipolar'

    -- Status do diagnóstico — reflete o raciocínio clínico no tempo
    status              VARCHAR(20) NOT NULL DEFAULT 'suspected'
                        CHECK (status IN (
                            'suspected',    -- hipótese em investigação
                            'confirmed',    -- diagnóstico estabelecido
                            'ruled_out',    -- descartado após investigação
                            'historical'   -- diagnóstico prévio, não ativo
                        )),

    registered_by       UUID NOT NULL REFERENCES auth.users(id),

    -- Período de vigência do diagnóstico
    started_at          DATE NOT NULL DEFAULT CURRENT_DATE,
    ended_at            DATE,                       -- NULL = diagnóstico ainda ativo

    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE patient_diagnoses IS
    'Linha do tempo diagnóstica. Cada linha é um episódio diagnóstico com status e período.';
COMMENT ON COLUMN patient_diagnoses.ended_at IS
    'NULL = diagnóstico ativo. Preencher para encerrar, não deletar.';


-- ------------------------------------------------------------
-- MODULES
-- Catálogo dos módulos disponíveis no app.
-- Tabela de referência — dados quase estáticos.
-- Pense como a lista de exames que um hospital oferece.
-- ------------------------------------------------------------
CREATE TABLE modules (
    id                  SERIAL PRIMARY KEY,
    code                VARCHAR(30) UNIQUE NOT NULL,
    display_name        VARCHAR(100) NOT NULL,
    description         TEXT,
    icon_name           VARCHAR(50),                -- nome do ícone no Flutter
    default_frequency   VARCHAR(20) CHECK (default_frequency IN (
                            'daily', 'as_needed', 'weekly'
                        )),
    is_available        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Catálogo inicial — os 8 módulos do MVP
INSERT INTO modules (code, display_name, description, default_frequency) VALUES
    ('mood',            'Humor',            'Registro diário de estado emocional',          'daily'),
    ('medication',      'Medicações',       'Adesão à medicação prescrita',                 'daily'),
    ('sleep',           'Sono',             'Qualidade e duração do sono',                  'daily'),
    ('diet',            'Dieta',            'Avaliação subjetiva da alimentação',            'daily'),
    ('meditation',      'Meditação',        'Prática de mindfulness e técnicas de calma',   'daily'),
    ('exercise',        'Exercícios',       'Atividade física realizada',                   'daily'),
    ('custom_symptoms', 'Sintomas',         'Sintomas personalizáveis por paciente',        'daily'),
    ('crisis',          'Registro de Crise','Registro de episódios de crise',               'as_needed');


-- ------------------------------------------------------------
-- PATIENT_MODULES
-- Quais módulos estão ativos para cada paciente.
-- Relação N:N entre patients e modules.
-- Implementa a ativação por paciente descrita no MVP.
-- ------------------------------------------------------------
CREATE TABLE patient_modules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    module_id       INTEGER NOT NULL REFERENCES modules(id),

    is_enabled      BOOLEAN NOT NULL DEFAULT TRUE,

    -- Array de horários de lembrete. Ex: {08:00, 20:00}
    reminder_times  TIME[],

    -- Configurações específicas do módulo em JSON flexível.
    -- Ex: {"scale": "1-10"} para mood, {"strict_schedule": true} para medication
    config          JSONB DEFAULT '{}',

    activated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deactivated_at  TIMESTAMPTZ,

    -- Um paciente não pode ter o mesmo módulo ativo duas vezes
    UNIQUE (patient_id, module_id)
);


-- ------------------------------------------------------------
-- MEDICATIONS
-- Prescrições ativas do paciente.
-- Separado de medication_records porque prescrição ≠ adesão.
-- Prescrição: o que foi prescrito (quase estático).
-- Adesão: o que foi tomado (dinâmico, diário).
-- ------------------------------------------------------------
CREATE TABLE medications (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

    name                VARCHAR(200) NOT NULL,      -- 'Quetiapina'
    dosage              VARCHAR(50),                -- '100mg'
    unit                VARCHAR(20),                -- 'mg', 'comprimido'

    frequency_per_day   INTEGER NOT NULL DEFAULT 1,
    scheduled_times     TIME[] NOT NULL,            -- {08:00, 20:00}

    prescribed_at       DATE NOT NULL DEFAULT CURRENT_DATE,
    discontinued_at     DATE,                       -- NULL = ainda em uso

    notes               TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- CUSTOM_SYMPTOMS
-- Sintomas personalizados definidos pelo médico ou paciente.
-- Ex: "Flashbacks", "Voz interna", "Agitação noturna"
-- ------------------------------------------------------------
CREATE TABLE custom_symptoms (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

    name            VARCHAR(100) NOT NULL,
    description     TEXT,

    -- Como o sintoma é medido
    scale_type      VARCHAR(20) NOT NULL DEFAULT 'numeric'
                    CHECK (scale_type IN (
                        'numeric',      -- escala 0-10
                        'boolean',      -- presente ou ausente
                        'frequency'     -- nunca / às vezes / sempre
                    )),

    scale_min       INTEGER DEFAULT 0,
    scale_max       INTEGER DEFAULT 10,

    -- Alerta médico se o valor ultrapassar esse limite
    alert_threshold INTEGER,

    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- BLOCO 3: REGISTROS DIÁRIOS
-- ============================================================


-- ------------------------------------------------------------
-- MOOD_RECORDS — Registros de Humor
-- ------------------------------------------------------------
CREATE TABLE mood_records (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

    -- record_date: data a que o registro SE REFERE (pode ser ontem)
    -- created_at:  quando foi salvo no servidor (sempre hoje)
    -- Essa distinção é crítica para relatórios clínicos corretos.
    record_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Escala 1-10 (1 = muito mal, 10 = excelente)
    score           SMALLINT NOT NULL CHECK (score BETWEEN 1 AND 10),

    -- Tags de emoção (multi-select no app)
    emotions        VARCHAR(50)[],

    notes           TEXT,

    -- Origem do registro para análise de adesão
    source          VARCHAR(20) DEFAULT 'manual'
                    CHECK (source IN ('manual', 'reminder', 'prompted')),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN mood_records.record_date IS
    'Data a que o registro se refere. Diferente de created_at (timestamp de inserção).';


-- ------------------------------------------------------------
-- SLEEP_RECORDS — Registros de Sono
-- Sono é biomarcador crítico em psiquiatria.
-- Um registro por dia (constraint UNIQUE).
-- ------------------------------------------------------------
CREATE TABLE sleep_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

    record_date         DATE NOT NULL DEFAULT CURRENT_DATE,

    sleep_time          TIME,                   -- hora que foi dormir
    wake_time           TIME,                   -- hora que acordou
    duration_minutes    INTEGER,                -- duração calculada ou informada

    quality_score       SMALLINT CHECK (quality_score BETWEEN 1 AND 5),

    -- Marcadores clínicos
    had_nightmares      BOOLEAN DEFAULT FALSE,
    had_insomnia        BOOLEAN DEFAULT FALSE,
    used_sleep_medication BOOLEAN DEFAULT FALSE,

    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Garante apenas um registro de sono por dia por paciente
    UNIQUE (patient_id, record_date)
);


-- ------------------------------------------------------------
-- MEDICATION_RECORDS — Registros de Adesão
-- Cada linha = uma tomada prevista (tomada ou não).
-- Isso permite calcular taxa de adesão por período.
-- ------------------------------------------------------------
CREATE TABLE medication_records (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    medication_id   UUID NOT NULL REFERENCES medications(id) ON DELETE RESTRICT,

    scheduled_at    TIMESTAMPTZ NOT NULL,       -- quando deveria ter tomado

    status          VARCHAR(30) NOT NULL DEFAULT 'pending'
                    CHECK (status IN (
                        'taken',                -- tomou no horário
                        'missed',               -- não tomou
                        'delayed',              -- tomou fora do horário
                        'skipped_intentional',  -- pulou intencionalmente
                        'pending'               -- ainda não chegou o horário
                    )),

    taken_at        TIMESTAMPTZ,                -- quando realmente tomou

    -- Por que não tomou — dado clínico valioso
    skip_reason     VARCHAR(50) CHECK (skip_reason IN (
                        'forgot', 'side_effects', 'felt_well',
                        'no_medication', 'other'
                    )),

    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- EXERCISE_RECORDS — Registros de Exercício Físico
-- ------------------------------------------------------------
CREATE TABLE exercise_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

    record_date         DATE NOT NULL DEFAULT CURRENT_DATE,

    exercise_type       VARCHAR(50),            -- 'caminhada', 'musculação', 'yoga'
    duration_minutes    INTEGER,
    intensity           VARCHAR(20) CHECK (intensity IN ('light', 'moderate', 'intense')),

    -- Como se sentiu após o exercício (1-5)
    mood_after          SMALLINT CHECK (mood_after BETWEEN 1 AND 5),

    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- MEDITATION_RECORDS — Registros de Meditação
-- ------------------------------------------------------------
CREATE TABLE meditation_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

    record_date         DATE NOT NULL DEFAULT CURRENT_DATE,

    duration_minutes    INTEGER NOT NULL,
    technique           VARCHAR(50),            -- 'mindfulness', 'respiração', 'guided'

    -- Concentração atingida (1-5)
    focus_score         SMALLINT CHECK (focus_score BETWEEN 1 AND 5),

    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- DIET_RECORDS — Registros de Dieta
-- Não é diário alimentar detalhado (seria scope creep para o MVP).
-- É avaliação subjetiva da qualidade alimentar do dia.
-- Marcadores clínicos relevantes para psiquiatria incluídos.
-- ------------------------------------------------------------
CREATE TABLE diet_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

    record_date         DATE NOT NULL DEFAULT CURRENT_DATE,

    quality_score       SMALLINT CHECK (quality_score BETWEEN 1 AND 5),

    -- Marcadores clínicos
    water_intake_ok     BOOLEAN,                -- hidratação adequada?
    skipped_meals       INTEGER,                -- quantas refeições pulou?
    had_binge           BOOLEAN,                -- episódio de compulsão?
    had_restriction     BOOLEAN,                -- restrição alimentar?

    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (patient_id, record_date)
);


-- ------------------------------------------------------------
-- SYMPTOM_RECORDS — Registros de Sintomas Customizados
-- O valor registrado depende do scale_type do sintoma.
-- ------------------------------------------------------------
CREATE TABLE symptom_records (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    symptom_id      UUID NOT NULL REFERENCES custom_symptoms(id) ON DELETE RESTRICT,

    record_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Apenas um dos campos abaixo será preenchido,
    -- dependendo do scale_type do symptom referenciado.
    numeric_value   DECIMAL(5,2),               -- para scale_type = 'numeric'
    boolean_value   BOOLEAN,                    -- para scale_type = 'boolean'
    frequency_value VARCHAR(20) CHECK (frequency_value IN (
                        'never', 'sometimes', 'often', 'always'
                    )),                         -- para scale_type = 'frequency'

    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ------------------------------------------------------------
-- CRISIS_RECORDS — Registros de Crise
-- Tabela mais crítica do sistema. Só dado clínico aqui.
-- O fluxo operacional de alerta fica em clinical_alerts.
-- Projetada para preenchimento rápido: paciente em crise
-- não tem paciência para formulários longos.
-- ------------------------------------------------------------
CREATE TABLE crisis_records (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id              UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

    occurred_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Intensidade da crise: 1 (leve) a 10 (emergência)
    intensity               SMALLINT NOT NULL CHECK (intensity BETWEEN 1 AND 10),

    crisis_types            VARCHAR(50)[],      -- multi-select
    -- Valores possíveis: 'anxiety', 'dissociation', 'suicidal_ideation',
    -- 'panic_attack', 'self_harm_urge', 'psychosis', 'other'

    -- Flag explícita para ideação suicida.
    -- Não fica "escondida" dentro do array — é indexável e filtrável.
    -- Gera alerta imediato de severidade 'critical'.
    has_suicidal_ideation   BOOLEAN NOT NULL DEFAULT FALSE,

    coping_used             VARCHAR(100)[],     -- o que foi feito durante/após
    -- Valores: 'breathing', 'called_someone', 'took_medication',
    -- 'went_to_er', 'other'

    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN crisis_records.has_suicidal_ideation IS
    'Flag explícita. Gera clinical_alert com severity=critical automaticamente via trigger.';


-- ============================================================
-- BLOCO 4: SISTEMA DE ALERTAS
-- ============================================================


-- ------------------------------------------------------------
-- CLINICAL_ALERTS — Sistema de Alertas Desacoplado
-- Separa o EVENTO CLÍNICO (o que aconteceu) do
-- FLUXO OPERACIONAL (o que foi feito a respeito).
--
-- source_type + source_record_id = referência polimórfica.
-- Qualquer tabela de registros pode gerar um alerta.
-- ------------------------------------------------------------
CREATE TABLE clinical_alerts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

    -- O que gerou o alerta
    source_type         VARCHAR(50) NOT NULL CHECK (source_type IN (
                            'crisis_record',        -- crise registrada
                            'suicidal_ideation',    -- ideação suicida (subconjunto de crise)
                            'medication_adherence', -- doses perdidas consecutivas
                            'mood_critical',        -- humor crítico por N dias
                            'symptom_threshold',    -- sintoma acima do threshold
                            'no_activity'           -- sem registro por N dias
                        )),

    -- ID do registro que originou o alerta (NULL se por ausência de dado)
    source_record_id    UUID,

    severity            VARCHAR(20) NOT NULL DEFAULT 'moderate'
                        CHECK (severity IN (
                            'low',      -- informativo — ver na próxima consulta
                            'moderate', -- atenção — contato em breve
                            'high',     -- urgente — contato nas próximas horas
                            'critical'  -- emergência (ex: ideação suicida ativa)
                        )),

    -- Ciclo de vida do alerta
    status              VARCHAR(20) NOT NULL DEFAULT 'open'
                        CHECK (status IN (
                            'open',             -- aguardando ação
                            'acknowledged',     -- médico viu e está tratando
                            'resolved',         -- situação resolvida
                            'false_positive'    -- médico marcou como falso positivo
                        )),

    acknowledged_by     UUID REFERENCES auth.users(id),
    acknowledged_at     TIMESTAMPTZ,
    resolved_by         UUID REFERENCES auth.users(id),
    resolved_at         TIMESTAMPTZ,
    resolution_notes    TEXT,

    -- Metadados de notificação
    notification_sent_at        TIMESTAMPTZ,
    notification_channel        VARCHAR(20) CHECK (notification_channel IN ('push', 'sms', 'email')),
    notification_attempts       SMALLINT DEFAULT 0,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE clinical_alerts IS
    'Fila de eventos que requerem atenção médica. Desacoplado dos eventos clínicos.';


-- ============================================================
-- BLOCO 5: AUDITORIA
-- ============================================================


-- ------------------------------------------------------------
-- AUDIT_LOGS — Rastreabilidade Obrigatória
-- CFM (Res. 2.314/2022) e LGPD exigem saber:
-- quem viu, quem alterou, o quê, quando, de onde.
--
-- Regras de imutabilidade:
-- - Nenhum usuário pode UPDATE ou DELETE nessa tabela
-- - Só INSERT via trigger automático
-- - Usamos BIGSERIAL (inteiro) porque o volume é alto
--   e UUID seria desperdício de espaço
-- ------------------------------------------------------------
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,

    user_id         UUID,                       -- NULL se ação automatizada
    user_role       VARCHAR(20) CHECK (user_role IN (
                        'patient', 'doctor', 'system', 'admin'
                    )),

    action          VARCHAR(10) NOT NULL CHECK (action IN (
                        'INSERT', 'UPDATE', 'DELETE', 'SELECT'
                    )),

    table_name      VARCHAR(100) NOT NULL,
    record_id       UUID,

    -- Snapshot do estado anterior e posterior
    old_values      JSONB,                      -- NULL para INSERT
    new_values      JSONB,                      -- NULL para DELETE

    -- Identificação da requisição (sem PII)
    ip_hash         TEXT,                       -- SHA-256 do IP
    user_agent_hash TEXT,

    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()

    -- Sem FK em user_id: logs sobrevivem mesmo se o usuário for deletado
);

COMMENT ON TABLE audit_logs IS
    'Log imutável de auditoria. Equivalente digital ao prontuário carimbado.';

-- Revoga permissão de alterar ou deletar logs de qualquer role
-- (o INSERT ainda funciona via trigger com SECURITY DEFINER)
REVOKE UPDATE, DELETE ON audit_logs FROM PUBLIC;
REVOKE UPDATE, DELETE ON audit_logs FROM anon;
REVOKE UPDATE, DELETE ON audit_logs FROM authenticated;


-- ============================================================
-- BLOCO 6: ÍNDICES DE PERFORMANCE
-- Sem índice, cada query varre a tabela inteira.
-- Com índice, é como ter uma aba no prontuário — acesso direto.
-- ============================================================

-- Queries mais frequentes: registros do paciente X nos últimos N dias
CREATE INDEX idx_mood_patient_date
    ON mood_records(patient_id, record_date DESC);

CREATE INDEX idx_sleep_patient_date
    ON sleep_records(patient_id, record_date DESC);

CREATE INDEX idx_medication_patient_scheduled
    ON medication_records(patient_id, scheduled_at DESC);

CREATE INDEX idx_crisis_patient_date
    ON crisis_records(patient_id, occurred_at DESC);

CREATE INDEX idx_exercise_patient_date
    ON exercise_records(patient_id, record_date DESC);

CREATE INDEX idx_symptom_records_patient_date
    ON symptom_records(patient_id, record_date DESC);

-- Para o sistema de alertas: crises com ideação não alertadas
CREATE INDEX idx_crisis_suicidal_unalerted
    ON crisis_records(has_suicidal_ideation, occurred_at DESC)
    WHERE has_suicidal_ideation = TRUE;

-- Para o painel do médico: alertas abertos por severidade
CREATE INDEX idx_alerts_open_severity
    ON clinical_alerts(patient_id, severity, created_at DESC)
    WHERE status = 'open';

-- Para alertas críticos não respondidos (fila de emergência)
CREATE INDEX idx_alerts_critical_open
    ON clinical_alerts(severity, created_at)
    WHERE status = 'open' AND severity IN ('high', 'critical');

-- Para relatórios: todos os pacientes ativos de um médico
CREATE INDEX idx_patients_doctor_active
    ON patients(doctor_id)
    WHERE is_active = TRUE;

-- Para diagnósticos ativos de um paciente
CREATE INDEX idx_diagnoses_patient_active
    ON patient_diagnoses(patient_id, status)
    WHERE ended_at IS NULL;

-- Auditoria: quem fez o quê em qual tabela
CREATE INDEX idx_audit_table_record
    ON audit_logs(table_name, record_id, occurred_at DESC);

CREATE INDEX idx_audit_user
    ON audit_logs(user_id, occurred_at DESC);
