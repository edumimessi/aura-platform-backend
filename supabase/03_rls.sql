-- ============================================================
-- AURA — Row Level Security (RLS)
-- Execute APÓS 02_triggers.sql
--
-- O que é RLS?
-- É um filtro automático e invisível que o PostgreSQL aplica
-- em TODA query antes de executá-la. Mesmo que o código do
-- backend esqueça de filtrar por patient_id, o banco garante
-- que cada usuário só vê seus próprios dados.
--
-- Analogia: imagine que cada linha da tabela tem uma etiqueta
-- dizendo "pertence ao paciente X". O RLS verifica essa etiqueta
-- antes de entregar qualquer dado, sem exceção.
--
-- Roles no AURA:
-- - 'anon':          usuário não autenticado (só pode fazer login)
-- - 'authenticated': usuário autenticado (paciente OU médico)
--
-- Como distinguimos paciente de médico?
-- Via app_metadata no JWT do Supabase.
-- O backend define isso ao criar o usuário.
-- ============================================================


-- ============================================================
-- HABILITAR RLS EM TODAS AS TABELAS CLÍNICAS
-- Sem isso, RLS não funciona — qualquer query retorna tudo.
-- ============================================================
ALTER TABLE patients              ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_consents      ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_devices       ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_diagnoses     ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_modules       ENABLE ROW LEVEL SECURITY;
ALTER TABLE medications           ENABLE ROW LEVEL SECURITY;
ALTER TABLE custom_symptoms       ENABLE ROW LEVEL SECURITY;
ALTER TABLE modules               ENABLE ROW LEVEL SECURITY;
ALTER TABLE mood_records          ENABLE ROW LEVEL SECURITY;
ALTER TABLE sleep_records         ENABLE ROW LEVEL SECURITY;
ALTER TABLE medication_records    ENABLE ROW LEVEL SECURITY;
ALTER TABLE exercise_records      ENABLE ROW LEVEL SECURITY;
ALTER TABLE meditation_records    ENABLE ROW LEVEL SECURITY;
ALTER TABLE diet_records          ENABLE ROW LEVEL SECURITY;
ALTER TABLE symptom_records       ENABLE ROW LEVEL SECURITY;
ALTER TABLE crisis_records        ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinical_alerts       ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs            ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- FUNÇÃO AUXILIAR: verificar se o usuário atual é médico
-- Lê app_metadata do JWT. O backend define isso no Supabase
-- ao criar a conta do médico.
-- ============================================================
CREATE OR REPLACE FUNCTION is_doctor()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN (
        auth.jwt() -> 'app_metadata' ->> 'role' = 'doctor'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- Função auxiliar: retorna o patient_id do usuário atual
CREATE OR REPLACE FUNCTION current_patient_id()
RETURNS UUID AS $$
BEGIN
    RETURN (
        SELECT id FROM patients
        WHERE auth_user_id = auth.uid()
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;


-- ============================================================
-- POLÍTICAS — TABELA PATIENTS
-- ============================================================

-- Paciente vê apenas seu próprio registro
CREATE POLICY patient_see_self ON patients
    FOR SELECT TO authenticated
    USING (auth_user_id = auth.uid());

-- Médico vê todos os seus pacientes
CREATE POLICY doctor_see_own_patients ON patients
    FOR SELECT TO authenticated
    USING (
        is_doctor() AND doctor_id = auth.uid()
    );

-- Apenas sistema/admin pode criar pacientes (via backend com service key)
-- Pacientes não se auto-cadastram na tabela patients — o backend faz isso.
CREATE POLICY system_insert_patients ON patients
    FOR INSERT TO service_role  -- service_role = a service key do Supabase
    WITH CHECK (TRUE);

-- Paciente pode atualizar apenas campos não-clínicos do próprio registro
-- Médico pode atualizar dados dos seus pacientes
CREATE POLICY update_patients ON patients
    FOR UPDATE TO authenticated
    USING (
        auth_user_id = auth.uid()       -- é o próprio paciente
        OR
        (is_doctor() AND doctor_id = auth.uid())  -- é o médico responsável
    );


-- ============================================================
-- POLÍTICAS — REGISTROS CLÍNICOS (mood, sleep, medication, etc.)
-- O padrão é o mesmo para todos:
-- - Paciente: vê e cria apenas os próprios registros
-- - Médico: vê (somente leitura) registros dos seus pacientes
-- ============================================================

-- Macro para criar as políticas padrão.
-- Vamos aplicar manualmente para cada tabela (mais explícito para o aprendizado).


-- MOOD_RECORDS
CREATE POLICY mood_patient_access ON mood_records
    FOR ALL TO authenticated
    USING (patient_id = current_patient_id())
    WITH CHECK (patient_id = current_patient_id());

CREATE POLICY mood_doctor_read ON mood_records
    FOR SELECT TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );

-- SLEEP_RECORDS
CREATE POLICY sleep_patient_access ON sleep_records
    FOR ALL TO authenticated
    USING (patient_id = current_patient_id())
    WITH CHECK (patient_id = current_patient_id());

CREATE POLICY sleep_doctor_read ON sleep_records
    FOR SELECT TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );

-- MEDICATION_RECORDS
CREATE POLICY medication_records_patient_access ON medication_records
    FOR ALL TO authenticated
    USING (patient_id = current_patient_id())
    WITH CHECK (patient_id = current_patient_id());

CREATE POLICY medication_records_doctor_read ON medication_records
    FOR SELECT TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );

-- EXERCISE_RECORDS
CREATE POLICY exercise_patient_access ON exercise_records
    FOR ALL TO authenticated
    USING (patient_id = current_patient_id())
    WITH CHECK (patient_id = current_patient_id());

CREATE POLICY exercise_doctor_read ON exercise_records
    FOR SELECT TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );

-- MEDITATION_RECORDS
CREATE POLICY meditation_patient_access ON meditation_records
    FOR ALL TO authenticated
    USING (patient_id = current_patient_id())
    WITH CHECK (patient_id = current_patient_id());

CREATE POLICY meditation_doctor_read ON meditation_records
    FOR SELECT TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );

-- DIET_RECORDS
CREATE POLICY diet_patient_access ON diet_records
    FOR ALL TO authenticated
    USING (patient_id = current_patient_id())
    WITH CHECK (patient_id = current_patient_id());

CREATE POLICY diet_doctor_read ON diet_records
    FOR SELECT TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );

-- CRISIS_RECORDS
CREATE POLICY crisis_patient_access ON crisis_records
    FOR ALL TO authenticated
    USING (patient_id = current_patient_id())
    WITH CHECK (patient_id = current_patient_id());

CREATE POLICY crisis_doctor_read ON crisis_records
    FOR SELECT TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );

-- SYMPTOM_RECORDS
CREATE POLICY symptom_records_patient_access ON symptom_records
    FOR ALL TO authenticated
    USING (patient_id = current_patient_id())
    WITH CHECK (patient_id = current_patient_id());

CREATE POLICY symptom_records_doctor_read ON symptom_records
    FOR SELECT TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );


-- ============================================================
-- POLÍTICAS — CONFIGURAÇÃO (medications, custom_symptoms, modules)
-- ============================================================

-- MEDICATIONS (prescrições)
-- Paciente vê suas próprias prescrições (somente leitura)
CREATE POLICY medications_patient_read ON medications
    FOR SELECT TO authenticated
    USING (patient_id = current_patient_id());

-- Médico gerencia prescrições dos seus pacientes
CREATE POLICY medications_doctor_manage ON medications
    FOR ALL TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    )
    WITH CHECK (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );

-- CUSTOM_SYMPTOMS
CREATE POLICY custom_symptoms_patient_read ON custom_symptoms
    FOR SELECT TO authenticated
    USING (patient_id = current_patient_id());

CREATE POLICY custom_symptoms_doctor_manage ON custom_symptoms
    FOR ALL TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );

-- MODULES (catálogo — somente leitura para todos autenticados)
CREATE POLICY modules_read_all ON modules
    FOR SELECT TO authenticated
    USING (is_available = TRUE);

-- PATIENT_MODULES (quais módulos cada paciente tem ativo)
CREATE POLICY patient_modules_patient_read ON patient_modules
    FOR SELECT TO authenticated
    USING (patient_id = current_patient_id());

CREATE POLICY patient_modules_doctor_manage ON patient_modules
    FOR ALL TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );


-- ============================================================
-- POLÍTICAS — CLINICAL_ALERTS
-- Paciente não vê seus próprios alertas (é dado operacional do médico)
-- Médico vê e gerencia alertas dos seus pacientes
-- ============================================================

CREATE POLICY alerts_doctor_manage ON clinical_alerts
    FOR ALL TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    )
    WITH CHECK (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );


-- ============================================================
-- POLÍTICAS — PATIENT_DIAGNOSES
-- Paciente vê seus próprios diagnósticos (transparência clínica)
-- Médico gerencia diagnósticos dos seus pacientes
-- ============================================================

CREATE POLICY diagnoses_patient_read ON patient_diagnoses
    FOR SELECT TO authenticated
    USING (patient_id = current_patient_id());

CREATE POLICY diagnoses_doctor_manage ON patient_diagnoses
    FOR ALL TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    )
    WITH CHECK (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );


-- ============================================================
-- POLÍTICAS — AUDIT_LOGS
-- Apenas médicos e admins podem ver logs de auditoria.
-- Ninguém pode modificar (garantido pelo REVOKE anterior).
-- ============================================================

CREATE POLICY audit_doctor_read ON audit_logs
    FOR SELECT TO authenticated
    USING (is_doctor());


-- ============================================================
-- POLÍTICAS — PATIENT_CONSENTS e PATIENT_DEVICES
-- ============================================================

CREATE POLICY consents_patient_manage ON patient_consents
    FOR ALL TO authenticated
    USING (patient_id = current_patient_id())
    WITH CHECK (patient_id = current_patient_id());

CREATE POLICY consents_doctor_read ON patient_consents
    FOR SELECT TO authenticated
    USING (
        is_doctor() AND patient_id IN (
            SELECT id FROM patients WHERE doctor_id = auth.uid()
        )
    );

CREATE POLICY devices_patient_manage ON patient_devices
    FOR ALL TO authenticated
    USING (patient_id = current_patient_id())
    WITH CHECK (patient_id = current_patient_id());
