-- ============================================================
-- AURA - Preflight Check do Banco Supabase/PostgreSQL
--
-- Objetivo:
-- Verificar o estado atual do banco ANTES de rodar qualquer schema.
--
-- Regras deste arquivo:
-- - Não altera dados.
-- - Não cria tabelas, funções, triggers ou policies.
-- - Não apaga nada.
-- - Executa apenas SELECTs de diagnóstico.
-- ============================================================


-- ============================================================
-- 1. TABELAS ESPERADAS
-- Verifica se as 18 tabelas principais existem em public.
-- ============================================================
WITH expected_tables(table_name) AS (
    VALUES
        ('patients'),
        ('patient_consents'),
        ('patient_devices'),
        ('patient_diagnoses'),
        ('modules'),
        ('patient_modules'),
        ('medications'),
        ('custom_symptoms'),
        ('mood_records'),
        ('sleep_records'),
        ('medication_records'),
        ('exercise_records'),
        ('meditation_records'),
        ('diet_records'),
        ('symptom_records'),
        ('crisis_records'),
        ('clinical_alerts'),
        ('audit_logs')
)
SELECT
    expected_tables.table_name,
    CASE
        WHEN information_schema.tables.table_name IS NULL THEN 'FALTANDO'
        ELSE 'OK'
    END AS status
FROM expected_tables
LEFT JOIN information_schema.tables
    ON information_schema.tables.table_schema = 'public'
    AND information_schema.tables.table_name = expected_tables.table_name
ORDER BY expected_tables.table_name;


-- ============================================================
-- 2. TRIGGERS ESPERADAS
-- Verifica se as triggers previstas em 02_triggers.sql existem.
-- ============================================================
WITH expected_triggers(trigger_name, table_name) AS (
    VALUES
        ('audit_mood_records', 'mood_records'),
        ('audit_sleep_records', 'sleep_records'),
        ('audit_medication_records', 'medication_records'),
        ('audit_crisis_records', 'crisis_records'),
        ('audit_symptom_records', 'symptom_records'),
        ('audit_patient_diagnoses', 'patient_diagnoses'),
        ('audit_patients', 'patients'),
        ('audit_exercise_records', 'exercise_records'),
        ('audit_diet_records', 'diet_records'),
        ('trigger_auto_alert_crisis', 'crisis_records'),
        ('trigger_auto_alert_mood', 'mood_records'),
        ('set_updated_at_patients', 'patients'),
        ('set_updated_at_patient_diagnoses', 'patient_diagnoses')
)
SELECT
    expected_triggers.trigger_name,
    expected_triggers.table_name,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM information_schema.triggers
            WHERE information_schema.triggers.trigger_schema = 'public'
              AND information_schema.triggers.trigger_name = expected_triggers.trigger_name
              AND information_schema.triggers.event_object_table = expected_triggers.table_name
        ) THEN 'OK'
        ELSE 'FALTANDO'
    END AS status
FROM expected_triggers
ORDER BY expected_triggers.table_name, expected_triggers.trigger_name;


-- ============================================================
-- 3. RLS NAS TABELAS SENSÍVEIS
-- Verifica se Row Level Security está ativado.
--
-- Observação:
-- O README do schema espera RLS em todas as 18 tabelas.
-- Mesmo modules sendo tabela de configuração, ela entra aqui para
-- garantir consistência com 03_rls.sql.
-- ============================================================
WITH expected_tables(table_name) AS (
    VALUES
        ('patients'),
        ('patient_consents'),
        ('patient_devices'),
        ('patient_diagnoses'),
        ('modules'),
        ('patient_modules'),
        ('medications'),
        ('custom_symptoms'),
        ('mood_records'),
        ('sleep_records'),
        ('medication_records'),
        ('exercise_records'),
        ('meditation_records'),
        ('diet_records'),
        ('symptom_records'),
        ('crisis_records'),
        ('clinical_alerts'),
        ('audit_logs')
)
SELECT
    expected_tables.table_name,
    CASE
        WHEN pg_class.relname IS NULL THEN 'TABELA FALTANDO'
        WHEN pg_class.relrowsecurity THEN 'OK'
        ELSE 'RLS DESATIVADO'
    END AS status
FROM expected_tables
LEFT JOIN pg_class
    ON pg_class.relname = expected_tables.table_name
    AND pg_class.relnamespace = (
        SELECT oid FROM pg_namespace WHERE nspname = 'public'
    )
ORDER BY expected_tables.table_name;


-- ============================================================
-- 4. POLICIES
-- Verifica se há pelo menos uma policy por tabela esperada.
-- Não valida ainda a lógica de cada policy; este é um preflight.
-- ============================================================
WITH expected_tables(table_name) AS (
    VALUES
        ('patients'),
        ('patient_consents'),
        ('patient_devices'),
        ('patient_diagnoses'),
        ('modules'),
        ('patient_modules'),
        ('medications'),
        ('custom_symptoms'),
        ('mood_records'),
        ('sleep_records'),
        ('medication_records'),
        ('exercise_records'),
        ('meditation_records'),
        ('diet_records'),
        ('symptom_records'),
        ('crisis_records'),
        ('clinical_alerts'),
        ('audit_logs')
),
policy_counts AS (
    SELECT
        tablename AS table_name,
        COUNT(*) AS policy_count
    FROM pg_policies
    WHERE schemaname = 'public'
    GROUP BY tablename
)
SELECT
    expected_tables.table_name,
    COALESCE(policy_counts.policy_count, 0) AS policy_count,
    CASE
        WHEN COALESCE(policy_counts.policy_count, 0) = 0 THEN 'SEM POLICY'
        ELSE 'OK'
    END AS status
FROM expected_tables
LEFT JOIN policy_counts
    ON policy_counts.table_name = expected_tables.table_name
ORDER BY expected_tables.table_name;


-- ============================================================
-- 5. RESUMO FINAL
-- Retorna uma visão consolidada do que está OK e do que falta.
-- ============================================================
WITH expected_tables(table_name) AS (
    VALUES
        ('patients'),
        ('patient_consents'),
        ('patient_devices'),
        ('patient_diagnoses'),
        ('modules'),
        ('patient_modules'),
        ('medications'),
        ('custom_symptoms'),
        ('mood_records'),
        ('sleep_records'),
        ('medication_records'),
        ('exercise_records'),
        ('meditation_records'),
        ('diet_records'),
        ('symptom_records'),
        ('crisis_records'),
        ('clinical_alerts'),
        ('audit_logs')
),
expected_triggers(trigger_name, table_name) AS (
    VALUES
        ('audit_mood_records', 'mood_records'),
        ('audit_sleep_records', 'sleep_records'),
        ('audit_medication_records', 'medication_records'),
        ('audit_crisis_records', 'crisis_records'),
        ('audit_symptom_records', 'symptom_records'),
        ('audit_patient_diagnoses', 'patient_diagnoses'),
        ('audit_patients', 'patients'),
        ('audit_exercise_records', 'exercise_records'),
        ('audit_diet_records', 'diet_records'),
        ('trigger_auto_alert_crisis', 'crisis_records'),
        ('trigger_auto_alert_mood', 'mood_records'),
        ('set_updated_at_patients', 'patients'),
        ('set_updated_at_patient_diagnoses', 'patient_diagnoses')
),
table_status AS (
    SELECT
        expected_tables.table_name,
        information_schema.tables.table_name IS NOT NULL AS exists_ok
    FROM expected_tables
    LEFT JOIN information_schema.tables
        ON information_schema.tables.table_schema = 'public'
        AND information_schema.tables.table_name = expected_tables.table_name
),
trigger_status AS (
    SELECT
        expected_triggers.trigger_name,
        EXISTS (
            SELECT 1
            FROM information_schema.triggers
            WHERE information_schema.triggers.trigger_schema = 'public'
              AND information_schema.triggers.trigger_name = expected_triggers.trigger_name
              AND information_schema.triggers.event_object_table = expected_triggers.table_name
        ) AS exists_ok
    FROM expected_triggers
),
rls_status AS (
    SELECT
        expected_tables.table_name,
        COALESCE(pg_class.relrowsecurity, FALSE) AS rls_ok
    FROM expected_tables
    LEFT JOIN pg_class
        ON pg_class.relname = expected_tables.table_name
        AND pg_class.relnamespace = (
            SELECT oid FROM pg_namespace WHERE nspname = 'public'
        )
),
policy_status AS (
    SELECT
        expected_tables.table_name,
        COALESCE(COUNT(pg_policies.policyname), 0) > 0 AS policies_ok
    FROM expected_tables
    LEFT JOIN pg_policies
        ON pg_policies.schemaname = 'public'
        AND pg_policies.tablename = expected_tables.table_name
    GROUP BY expected_tables.table_name
),
summary AS (
    SELECT
        'Tabelas esperadas' AS item,
        COUNT(*) FILTER (WHERE exists_ok) AS ok,
        COUNT(*) FILTER (WHERE NOT exists_ok) AS faltando
    FROM table_status

    UNION ALL

    SELECT
        'Triggers esperadas' AS item,
        COUNT(*) FILTER (WHERE exists_ok) AS ok,
        COUNT(*) FILTER (WHERE NOT exists_ok) AS faltando
    FROM trigger_status

    UNION ALL

    SELECT
        'RLS ativado' AS item,
        COUNT(*) FILTER (WHERE rls_ok) AS ok,
        COUNT(*) FILTER (WHERE NOT rls_ok) AS faltando
    FROM rls_status

    UNION ALL

    SELECT
        'Tabelas com policies' AS item,
        COUNT(*) FILTER (WHERE policies_ok) AS ok,
        COUNT(*) FILTER (WHERE NOT policies_ok) AS faltando
    FROM policy_status
)
SELECT
    item,
    ok,
    faltando,
    CASE
        WHEN faltando = 0 THEN 'OK'
        ELSE 'REVISAR'
    END AS status
FROM summary
ORDER BY item;
