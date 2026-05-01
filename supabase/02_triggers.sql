-- ============================================================
-- AURA — Triggers e Funções Automáticas
-- Execute APÓS o 01_schema.sql
--
-- Este arquivo configura dois tipos de automação:
-- 1. Auditoria automática: qualquer INSERT/UPDATE/DELETE em
--    tabelas clínicas gera um log em audit_logs.
-- 2. Alertas automáticos: crises com ideação suicida geram
--    um clinical_alert de severidade 'critical' imediatamente.
--
-- Por que triggers e não lógica no FastAPI?
-- Porque o banco é a última linha de defesa. Se alguém
-- acessar o banco diretamente (backup, migração, etc),
-- a auditoria ainda funciona. Se depender só do backend,
-- qualquer acesso direto ao banco fica sem rastro.
-- ============================================================


-- ============================================================
-- FUNÇÃO DE AUDITORIA
-- Chamada automaticamente por todos os triggers de auditoria.
-- SECURITY DEFINER: roda com permissões do dono da função
-- (não do usuário que fez a ação) — necessário para INSERT
-- em audit_logs mesmo quando o usuário não tem essa permissão.
-- ============================================================
CREATE OR REPLACE FUNCTION fn_audit_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs (
        user_id,
        user_role,
        action,
        table_name,
        record_id,
        old_values,
        new_values,
        ip_hash
    ) VALUES (
        -- auth.uid() retorna o UUID do usuário autenticado pelo Supabase Auth.
        -- NULL se a ação veio do sistema (ex: outro trigger).
        auth.uid(),

        -- Role passada pela aplicação via SET LOCAL.
        -- O backend faz: SET LOCAL app.user_role = 'patient';
        -- antes de cada operação. Se não definida, usa 'system'.
        COALESCE(current_setting('app.user_role', true), 'system'),

        -- TG_OP: variável especial do trigger = 'INSERT', 'UPDATE' ou 'DELETE'
        TG_OP,

        -- TG_TABLE_NAME: nome da tabela que disparou o trigger
        TG_TABLE_NAME,

        -- ID do registro afetado
        -- NEW existe em INSERT e UPDATE; OLD existe em UPDATE e DELETE
        COALESCE(NEW.id, OLD.id),

        -- Estado anterior (NULL em INSERT — não havia estado antes)
        CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE to_jsonb(OLD) END,

        -- Estado novo (NULL em DELETE — não haverá estado depois)
        CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE to_jsonb(NEW) END,

        -- Hash do IP passado pelo backend via SET LOCAL
        current_setting('app.ip_hash', true)
    );

    -- RETURN NEW para INSERT/UPDATE, OLD para DELETE.
    -- COALESCE retorna o primeiro não-nulo.
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION fn_audit_trigger() IS
    'Trigger de auditoria universal. Chamado por todos os triggers clínicos.';


-- ============================================================
-- APLICAÇÃO DOS TRIGGERS DE AUDITORIA
-- Cada tabela clínica crítica recebe o trigger.
-- Tabelas de menor criticidade (exercise, meditation, diet)
-- também são auditadas — dado médico é dado médico.
-- ============================================================

CREATE TRIGGER audit_mood_records
    AFTER INSERT OR UPDATE OR DELETE ON mood_records
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

CREATE TRIGGER audit_sleep_records
    AFTER INSERT OR UPDATE OR DELETE ON sleep_records
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

CREATE TRIGGER audit_medication_records
    AFTER INSERT OR UPDATE OR DELETE ON medication_records
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

CREATE TRIGGER audit_crisis_records
    AFTER INSERT OR UPDATE OR DELETE ON crisis_records
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

CREATE TRIGGER audit_symptom_records
    AFTER INSERT OR UPDATE OR DELETE ON symptom_records
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

CREATE TRIGGER audit_patient_diagnoses
    AFTER INSERT OR UPDATE OR DELETE ON patient_diagnoses
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

CREATE TRIGGER audit_patients
    AFTER INSERT OR UPDATE OR DELETE ON patients
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

CREATE TRIGGER audit_exercise_records
    AFTER INSERT OR UPDATE OR DELETE ON exercise_records
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();

CREATE TRIGGER audit_diet_records
    AFTER INSERT OR UPDATE OR DELETE ON diet_records
    FOR EACH ROW EXECUTE FUNCTION fn_audit_trigger();


-- ============================================================
-- TRIGGER DE ALERTA AUTOMÁTICO — CRISE COM IDEAÇÃO SUICIDA
--
-- Quando um paciente registra uma crise com ideação suicida,
-- um clinical_alert de severidade 'critical' é criado
-- imediatamente, no mesmo momento da inserção.
--
-- Por que no banco e não no backend?
-- Porque garante que o alerta é criado mesmo que o backend
-- falhe após o INSERT (ex: timeout, crash). O banco é atômico:
-- ou os dois acontecem juntos, ou nenhum acontece.
-- ============================================================
CREATE OR REPLACE FUNCTION fn_auto_alert_crisis()
RETURNS TRIGGER AS $$
BEGIN
    -- Só cria alerta em INSERT (não em UPDATE de crise existente)
    IF TG_OP = 'INSERT' THEN

        -- Alerta para qualquer crise de intensidade alta (>= 7)
        IF NEW.intensity >= 7 THEN
            INSERT INTO clinical_alerts (
                patient_id,
                source_type,
                source_record_id,
                severity,
                status
            ) VALUES (
                NEW.patient_id,
                'crisis_record',
                NEW.id,
                CASE
                    WHEN NEW.has_suicidal_ideation = TRUE THEN 'critical'
                    WHEN NEW.intensity >= 9 THEN 'critical'
                    WHEN NEW.intensity >= 7 THEN 'high'
                    ELSE 'moderate'
                END,
                'open'
            );

        -- Alerta para QUALQUER crise com ideação suicida (independente da intensidade)
        ELSIF NEW.has_suicidal_ideation = TRUE THEN
            INSERT INTO clinical_alerts (
                patient_id,
                source_type,
                source_record_id,
                severity,
                status
            ) VALUES (
                NEW.patient_id,
                'suicidal_ideation',
                NEW.id,
                'critical',
                'open'
            );
        END IF;

    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION fn_auto_alert_crisis() IS
    'Gera clinical_alert automaticamente quando crise >= 7 ou ideação suicida presente.';

CREATE TRIGGER trigger_auto_alert_crisis
    AFTER INSERT ON crisis_records
    FOR EACH ROW EXECUTE FUNCTION fn_auto_alert_crisis();


-- ============================================================
-- TRIGGER DE ALERTA — HUMOR CRÍTICO
-- Se humor <= 2, gera alerta 'high'.
-- Se humor = 1, gera alerta 'critical'.
-- Threshold configurável aqui por enquanto.
-- Em v1.1: mover para configuração por paciente.
-- ============================================================
CREATE OR REPLACE FUNCTION fn_auto_alert_mood()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.score <= 2 THEN
        INSERT INTO clinical_alerts (
            patient_id,
            source_type,
            source_record_id,
            severity,
            status
        ) VALUES (
            NEW.patient_id,
            'mood_critical',
            NEW.id,
            CASE WHEN NEW.score = 1 THEN 'critical' ELSE 'high' END,
            'open'
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trigger_auto_alert_mood
    AFTER INSERT ON mood_records
    FOR EACH ROW EXECUTE FUNCTION fn_auto_alert_mood();


-- ============================================================
-- TRIGGER — updated_at automático
-- Mantém o campo updated_at sempre atualizado sem depender
-- do código da aplicação.
-- ============================================================
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at_patients
    BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

CREATE TRIGGER set_updated_at_patient_diagnoses
    BEFORE UPDATE ON patient_diagnoses
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
