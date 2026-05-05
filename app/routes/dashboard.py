"""
dashboard.py — Endpoints do Dashboard Médico

Fornece dados agregados para o médico visualizar o estado
clínico dos seus pacientes: adesão, alertas, registros recentes.

Todos os endpoints exigem que o usuário autenticado seja médico
(doctor_id nos pacientes). Nenhum paciente pode acessar esses endpoints.

Endpoints:
    GET  /api/dashboard/patients              — Lista pacientes com status de adesão
    GET  /api/dashboard/patients/{id}/summary — Resumo clínico de um paciente
    GET  /api/dashboard/alerts                — Alertas clínicos abertos
    PUT  /api/dashboard/alerts/{id}/resolve   — Resolver alerta
    GET  /api/dashboard/patients/{id}/modules — Módulos ativos do paciente
    PUT  /api/dashboard/patients/{id}/modules — Ativar/desativar módulo
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from app.auth import verify_supabase_token, get_user_id
from app.database import supabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard Médico"])


# ============================================================
# MODELS
# ============================================================

class PatientListItem(BaseModel):
    """Item da lista de pacientes no dashboard."""
    id: str
    full_name: str
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    is_active: bool
    last_record_date: Optional[str] = None
    days_without_record: Optional[int] = None
    adherence_status: str  # 'ok', 'warning', 'alert', 'critical'
    open_alerts_count: int = 0


class PatientSummary(BaseModel):
    """Resumo clínico de um paciente para o dashboard."""
    patient_id: str
    full_name: str
    last_mood_score: Optional[float] = None
    last_mood_date: Optional[str] = None
    avg_mood_7d: Optional[float] = None
    avg_mood_30d: Optional[float] = None
    last_sleep_hours: Optional[float] = None
    last_sleep_quality: Optional[int] = None
    medication_adherence_7d: Optional[float] = None  # % de doses tomadas
    open_alerts: List[dict] = []
    recent_crisis_count: int = 0
    days_without_record: int = 0


class AlertItem(BaseModel):
    """Alerta clínico aberto."""
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    alert_type: str
    severity: str
    message: str
    created_at: str
    status: str


class ModuleConfig(BaseModel):
    """Configuração de módulo de um paciente."""
    module_code: str
    is_active: bool
    config: Optional[dict] = None


class ModuleToggle(BaseModel):
    """Ativar ou desativar um módulo."""
    module_code: str
    is_active: bool


# ============================================================
# HELPER
# ============================================================

def _verify_doctor(doctor_id: str):
    """Verifica se o usuário autenticado é médico (tem pelo menos um paciente)."""
    # No MVP, qualquer usuário que tenha pacientes cadastrados é tratado como médico.
    # Na Fase 4 (multi-médicos), isso será substituído por uma tabela de roles.
    pass


def _get_patient_or_403(patient_id: str, doctor_id: str) -> dict:
    """Busca paciente e verifica se pertence ao médico autenticado."""
    resp = supabase.table("patients") \
        .select("id, full_name, birth_date, gender, is_active") \
        .eq("id", patient_id) \
        .eq("doctor_id", doctor_id) \
        .single() \
        .execute()

    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Paciente não encontrado ou não pertence a este médico."
        )
    return resp.data


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/patients", response_model=List[PatientListItem])
async def list_patients_dashboard(
    doctor_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token)
):
    """
    Lista todos os pacientes do médico com status de adesão.

    Calcula automaticamente:
    - Dias sem registro
    - Status de adesão: ok / warning (2d) / alert (3d) / critical (5d+)
    - Número de alertas clínicos abertos
    """
    # Buscar pacientes do médico
    patients_resp = supabase.table("patients") \
        .select("id, full_name, birth_date, gender, is_active") \
        .eq("doctor_id", doctor_id) \
        .eq("is_active", True) \
        .order("full_name") \
        .execute()

    if not patients_resp.data:
        return []

    result = []
    today = datetime.utcnow().date()

    for patient in patients_resp.data:
        patient_id = patient["id"]

        # Buscar último registro de humor (proxy de adesão geral)
        last_mood = supabase.table("mood_records") \
            .select("record_date") \
            .eq("patient_id", patient_id) \
            .order("record_date", desc=True) \
            .limit(1) \
            .execute()

        last_record_date = None
        days_without = None
        adherence_status = "ok"

        if last_mood.data:
            last_record_date = last_mood.data[0]["record_date"]
            try:
                last_date = datetime.strptime(last_record_date, "%Y-%m-%d").date()
                days_without = (today - last_date).days
            except Exception:
                days_without = None
        else:
            # Nunca registrou
            days_without = 999

        # Classificar adesão
        if days_without is not None:
            if days_without >= 5:
                adherence_status = "critical"
            elif days_without >= 3:
                adherence_status = "alert"
            elif days_without >= 2:
                adherence_status = "warning"
            else:
                adherence_status = "ok"

        # Contar alertas abertos
        alerts_resp = supabase.table("clinical_alerts") \
            .select("id", count="exact") \
            .eq("patient_id", patient_id) \
            .eq("status", "open") \
            .execute()

        open_alerts_count = alerts_resp.count or 0

        result.append(PatientListItem(
            id=patient_id,
            full_name=patient.get("full_name", "Paciente"),
            birth_date=patient.get("birth_date"),
            gender=patient.get("gender"),
            is_active=patient.get("is_active", True),
            last_record_date=last_record_date,
            days_without_record=days_without if days_without != 999 else None,
            adherence_status=adherence_status,
            open_alerts_count=open_alerts_count,
        ))

    return result


@router.get("/patients/{patient_id}/summary", response_model=PatientSummary)
async def get_patient_summary(
    patient_id: str,
    doctor_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token)
):
    """
    Resumo clínico de um paciente para uso na consulta.

    Inclui: humor dos últimos 7 e 30 dias, sono, adesão a medicações,
    alertas abertos e crises recentes.
    """
    patient = _get_patient_or_403(patient_id, doctor_id)
    today = datetime.utcnow().date()
    date_7d = (today - timedelta(days=7)).isoformat()
    date_30d = (today - timedelta(days=30)).isoformat()

    # Humor — último registro
    last_mood_resp = supabase.table("mood_records") \
        .select("mood_score, record_date") \
        .eq("patient_id", patient_id) \
        .order("record_date", desc=True) \
        .limit(1) \
        .execute()

    last_mood_score = None
    last_mood_date = None
    if last_mood_resp.data:
        last_mood_score = last_mood_resp.data[0].get("mood_score")
        last_mood_date = last_mood_resp.data[0].get("record_date")

    # Humor — média 7 dias
    mood_7d_resp = supabase.table("mood_records") \
        .select("mood_score") \
        .eq("patient_id", patient_id) \
        .gte("record_date", date_7d) \
        .execute()

    avg_mood_7d = None
    if mood_7d_resp.data:
        scores = [r["mood_score"] for r in mood_7d_resp.data if r.get("mood_score")]
        avg_mood_7d = round(sum(scores) / len(scores), 1) if scores else None

    # Humor — média 30 dias
    mood_30d_resp = supabase.table("mood_records") \
        .select("mood_score") \
        .eq("patient_id", patient_id) \
        .gte("record_date", date_30d) \
        .execute()

    avg_mood_30d = None
    if mood_30d_resp.data:
        scores = [r["mood_score"] for r in mood_30d_resp.data if r.get("mood_score")]
        avg_mood_30d = round(sum(scores) / len(scores), 1) if scores else None

    # Sono — último registro
    last_sleep_resp = supabase.table("sleep_records") \
        .select("duration_hours, quality_score") \
        .eq("patient_id", patient_id) \
        .order("record_date", desc=True) \
        .limit(1) \
        .execute()

    last_sleep_hours = None
    last_sleep_quality = None
    if last_sleep_resp.data:
        last_sleep_hours = last_sleep_resp.data[0].get("duration_hours")
        last_sleep_quality = last_sleep_resp.data[0].get("quality_score")

    # Medicação — adesão nos últimos 7 dias (% de doses tomadas)
    med_resp = supabase.table("medication_records") \
        .select("status") \
        .eq("patient_id", patient_id) \
        .gte("scheduled_at", f"{date_7d}T00:00:00") \
        .execute()

    medication_adherence_7d = None
    if med_resp.data:
        total = len(med_resp.data)
        taken = sum(1 for r in med_resp.data if r.get("status") == "taken")
        medication_adherence_7d = round((taken / total) * 100, 1) if total > 0 else None

    # Alertas abertos
    alerts_resp = supabase.table("clinical_alerts") \
        .select("id, alert_type, severity, message, created_at, status") \
        .eq("patient_id", patient_id) \
        .eq("status", "open") \
        .order("created_at", desc=True) \
        .limit(10) \
        .execute()

    open_alerts = alerts_resp.data or []

    # Crises recentes (30 dias)
    crisis_resp = supabase.table("crisis_records") \
        .select("id", count="exact") \
        .eq("patient_id", patient_id) \
        .gte("occurred_at", f"{date_30d}T00:00:00") \
        .execute()

    recent_crisis_count = crisis_resp.count or 0

    # Dias sem registro
    days_without = 0
    if last_mood_date:
        try:
            last_date = datetime.strptime(last_mood_date, "%Y-%m-%d").date()
            days_without = (today - last_date).days
        except Exception:
            pass

    return PatientSummary(
        patient_id=patient_id,
        full_name=patient.get("full_name", "Paciente"),
        last_mood_score=last_mood_score,
        last_mood_date=last_mood_date,
        avg_mood_7d=avg_mood_7d,
        avg_mood_30d=avg_mood_30d,
        last_sleep_hours=last_sleep_hours,
        last_sleep_quality=last_sleep_quality,
        medication_adherence_7d=medication_adherence_7d,
        open_alerts=open_alerts,
        recent_crisis_count=recent_crisis_count,
        days_without_record=days_without,
    )


@router.get("/alerts", response_model=List[AlertItem])
async def list_open_alerts(
    doctor_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token)
):
    """
    Lista todos os alertas clínicos abertos dos pacientes do médico.
    Ordenados por severidade (critical primeiro) e data.
    """
    # Buscar IDs dos pacientes do médico
    patients_resp = supabase.table("patients") \
        .select("id, full_name") \
        .eq("doctor_id", doctor_id) \
        .eq("is_active", True) \
        .execute()

    if not patients_resp.data:
        return []

    patient_ids = [p["id"] for p in patients_resp.data]
    patient_names = {p["id"]: p["full_name"] for p in patients_resp.data}

    # Buscar alertas abertos
    alerts_resp = supabase.table("clinical_alerts") \
        .select("id, patient_id, alert_type, severity, message, created_at, status") \
        .in_("patient_id", patient_ids) \
        .eq("status", "open") \
        .order("created_at", desc=True) \
        .limit(50) \
        .execute()

    if not alerts_resp.data:
        return []

    # Ordenar: critical > high > medium > low
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_alerts = sorted(
        alerts_resp.data,
        key=lambda a: severity_order.get(a.get("severity", "low"), 3)
    )

    return [
        AlertItem(
            id=a["id"],
            patient_id=a["patient_id"],
            patient_name=patient_names.get(a["patient_id"]),
            alert_type=a.get("alert_type", ""),
            severity=a.get("severity", "low"),
            message=a.get("message", ""),
            created_at=a.get("created_at", ""),
            status=a.get("status", "open"),
        )
        for a in sorted_alerts
    ]


@router.put("/alerts/{alert_id}/resolve", status_code=status.HTTP_200_OK)
async def resolve_alert(
    alert_id: str,
    doctor_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token)
):
    """
    Marca um alerta clínico como resolvido.
    Só o médico responsável pelo paciente pode resolver.
    """
    # Verificar que o alerta pertence a um paciente deste médico
    alert_resp = supabase.table("clinical_alerts") \
        .select("id, patient_id") \
        .eq("id", alert_id) \
        .single() \
        .execute()

    if not alert_resp.data:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")

    patient_id = alert_resp.data["patient_id"]
    _get_patient_or_403(patient_id, doctor_id)

    # Resolver alerta
    supabase.table("clinical_alerts") \
        .update({
            "status": "resolved",
            "resolved_at": datetime.utcnow().isoformat(),
            "resolved_by": doctor_id,
        }) \
        .eq("id", alert_id) \
        .execute()

    return {"message": "Alerta resolvido com sucesso."}


@router.get("/patients/{patient_id}/modules")
async def get_patient_modules(
    patient_id: str,
    doctor_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token)
):
    """
    Retorna os módulos ativos/inativos de um paciente.
    Permite ao médico ver quais módulos estão habilitados.
    """
    _get_patient_or_403(patient_id, doctor_id)

    modules_resp = supabase.table("patient_modules") \
        .select("module_id, is_active, config, modules(code, name, description)") \
        .eq("patient_id", patient_id) \
        .execute()

    return modules_resp.data or []


@router.put("/patients/{patient_id}/modules", status_code=status.HTTP_200_OK)
async def toggle_patient_module(
    patient_id: str,
    toggle: ModuleToggle,
    doctor_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token)
):
    """
    Ativa ou desativa um módulo para um paciente específico.
    Somente o médico responsável pode alterar.
    """
    _get_patient_or_403(patient_id, doctor_id)

    # Buscar o module_id pelo código
    module_resp = supabase.table("modules") \
        .select("id") \
        .eq("code", toggle.module_code) \
        .single() \
        .execute()

    if not module_resp.data:
        raise HTTPException(status_code=404, detail=f"Módulo '{toggle.module_code}' não encontrado.")

    module_id = module_resp.data["id"]

    # Verificar se já existe registro em patient_modules
    existing = supabase.table("patient_modules") \
        .select("id") \
        .eq("patient_id", patient_id) \
        .eq("module_id", module_id) \
        .single() \
        .execute()

    if existing.data:
        # Atualizar
        supabase.table("patient_modules") \
            .update({"is_active": toggle.is_active}) \
            .eq("id", existing.data["id"]) \
            .execute()
    else:
        # Inserir
        supabase.table("patient_modules").insert({
            "patient_id": patient_id,
            "module_id": module_id,
            "is_active": toggle.is_active,
        }).execute()

    action = "ativado" if toggle.is_active else "desativado"
    return {"message": f"Módulo '{toggle.module_code}' {action} com sucesso."}
