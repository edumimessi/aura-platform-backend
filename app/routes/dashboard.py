"""
dashboard.py - Endpoints do Dashboard Medico.

Fornece dados agregados usando os nomes de colunas existentes no schema SQL.
"""

from datetime import datetime, timedelta
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import get_user_id, verify_supabase_token
from app.database import supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard Medico"])


class PatientListItem(BaseModel):
    id: str
    full_name: str
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    is_active: bool
    last_record_date: Optional[str] = None
    days_without_record: Optional[int] = None
    adherence_status: str
    open_alerts_count: int = 0


class PatientSummary(BaseModel):
    patient_id: str
    full_name: str
    last_mood_score: Optional[float] = None
    last_mood_date: Optional[str] = None
    avg_mood_7d: Optional[float] = None
    avg_mood_30d: Optional[float] = None
    last_sleep_hours: Optional[float] = None
    last_sleep_quality: Optional[int] = None
    medication_adherence_7d: Optional[float] = None
    open_alerts: List[dict] = []
    recent_crisis_count: int = 0
    days_without_record: int = 0


class AlertItem(BaseModel):
    id: str
    patient_id: str
    patient_name: Optional[str] = None
    alert_type: str
    severity: str
    message: str
    created_at: str
    status: str


class ModuleToggle(BaseModel):
    module_code: str
    is_active: bool


def _patient_label(patient: dict) -> str:
    return patient.get("full_name") or f"Paciente {patient['id'][:8]}"


def _alert_message(alert: dict) -> str:
    labels = {
        "crisis_record": "Registro de crise requer atencao.",
        "suicidal_ideation": "Ideacao suicida registrada. Prioridade critica.",
        "medication_adherence": "Possivel baixa adesao medicamentosa.",
        "mood_critical": "Humor critico registrado.",
        "symptom_threshold": "Sintoma acima do limite configurado.",
        "no_activity": "Paciente sem registros recentes.",
    }
    return labels.get(alert.get("source_type"), "Alerta clinico aberto.")


def _get_patient_or_403(patient_id: str, doctor_id: str) -> dict:
    resp = (
        supabase.table("patients")
        .select("id, birth_date, gender, is_active")
        .eq("id", patient_id)
        .eq("doctor_id", doctor_id)
        .single()
        .execute()
    )

    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Paciente nao encontrado ou nao pertence a este medico.",
        )
    return resp.data


def _days_since(record_date: Optional[str]) -> Optional[int]:
    if not record_date:
        return None
    try:
        last_date = datetime.strptime(record_date, "%Y-%m-%d").date()
        return (datetime.utcnow().date() - last_date).days
    except Exception:
        return None


def _adherence_status(days_without: Optional[int]) -> str:
    if days_without is None:
        return "critical"
    if days_without >= 5:
        return "critical"
    if days_without >= 3:
        return "alert"
    if days_without >= 2:
        return "warning"
    return "ok"


def _average_score(records: list[dict], field: str) -> Optional[float]:
    scores = [record[field] for record in records if record.get(field) is not None]
    return round(sum(scores) / len(scores), 1) if scores else None


@router.get("/patients", response_model=List[PatientListItem])
async def list_patients_dashboard(
    doctor_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token),
):
    patients_resp = (
        supabase.table("patients")
        .select("id, birth_date, gender, is_active, created_at")
        .eq("doctor_id", doctor_id)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .execute()
    )

    result = []
    for patient in patients_resp.data or []:
        patient_id = patient["id"]

        last_mood = (
            supabase.table("mood_records")
            .select("record_date")
            .eq("patient_id", patient_id)
            .order("record_date", desc=True)
            .limit(1)
            .execute()
        )
        last_record_date = last_mood.data[0]["record_date"] if last_mood.data else None
        days_without = _days_since(last_record_date)

        alerts_resp = (
            supabase.table("clinical_alerts")
            .select("id", count="exact")
            .eq("patient_id", patient_id)
            .eq("status", "open")
            .execute()
        )

        result.append(
            PatientListItem(
                id=patient_id,
                full_name=_patient_label(patient),
                birth_date=patient.get("birth_date"),
                gender=patient.get("gender"),
                is_active=patient.get("is_active", True),
                last_record_date=last_record_date,
                days_without_record=days_without,
                adherence_status=_adherence_status(days_without),
                open_alerts_count=alerts_resp.count or 0,
            )
        )

    return result


@router.get("/patients/{patient_id}/summary", response_model=PatientSummary)
async def get_patient_summary(
    patient_id: str,
    doctor_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token),
):
    patient = _get_patient_or_403(patient_id, doctor_id)
    today = datetime.utcnow().date()
    date_7d = (today - timedelta(days=7)).isoformat()
    date_30d = (today - timedelta(days=30)).isoformat()

    last_mood_resp = (
        supabase.table("mood_records")
        .select("score, record_date")
        .eq("patient_id", patient_id)
        .order("record_date", desc=True)
        .limit(1)
        .execute()
    )
    last_mood = last_mood_resp.data[0] if last_mood_resp.data else {}
    last_mood_date = last_mood.get("record_date")

    mood_7d_resp = (
        supabase.table("mood_records")
        .select("score")
        .eq("patient_id", patient_id)
        .gte("record_date", date_7d)
        .execute()
    )
    mood_30d_resp = (
        supabase.table("mood_records")
        .select("score")
        .eq("patient_id", patient_id)
        .gte("record_date", date_30d)
        .execute()
    )

    last_sleep_resp = (
        supabase.table("sleep_records")
        .select("duration_minutes, quality_score")
        .eq("patient_id", patient_id)
        .order("record_date", desc=True)
        .limit(1)
        .execute()
    )
    last_sleep = last_sleep_resp.data[0] if last_sleep_resp.data else {}
    duration_minutes = last_sleep.get("duration_minutes")

    med_resp = (
        supabase.table("medication_records")
        .select("status")
        .eq("patient_id", patient_id)
        .gte("scheduled_at", f"{date_7d}T00:00:00")
        .execute()
    )
    medication_adherence_7d = None
    if med_resp.data:
        total = len(med_resp.data)
        taken = sum(1 for record in med_resp.data if record.get("status") == "taken")
        medication_adherence_7d = round((taken / total) * 100, 1) if total else None

    alerts_resp = (
        supabase.table("clinical_alerts")
        .select("id, source_type, severity, created_at, status")
        .eq("patient_id", patient_id)
        .eq("status", "open")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    open_alerts = [
        {
            **alert,
            "alert_type": alert.get("source_type", "clinical_alert"),
            "message": _alert_message(alert),
        }
        for alert in (alerts_resp.data or [])
    ]

    crisis_resp = (
        supabase.table("crisis_records")
        .select("id", count="exact")
        .eq("patient_id", patient_id)
        .gte("occurred_at", f"{date_30d}T00:00:00")
        .execute()
    )

    return PatientSummary(
        patient_id=patient_id,
        full_name=_patient_label(patient),
        last_mood_score=last_mood.get("score"),
        last_mood_date=last_mood_date,
        avg_mood_7d=_average_score(mood_7d_resp.data or [], "score"),
        avg_mood_30d=_average_score(mood_30d_resp.data or [], "score"),
        last_sleep_hours=round(duration_minutes / 60, 1) if duration_minutes else None,
        last_sleep_quality=last_sleep.get("quality_score"),
        medication_adherence_7d=medication_adherence_7d,
        open_alerts=open_alerts,
        recent_crisis_count=crisis_resp.count or 0,
        days_without_record=_days_since(last_mood_date) or 0,
    )


@router.get("/alerts", response_model=List[AlertItem])
async def list_open_alerts(
    doctor_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token),
):
    patients_resp = (
        supabase.table("patients")
        .select("id")
        .eq("doctor_id", doctor_id)
        .eq("is_active", True)
        .execute()
    )

    if not patients_resp.data:
        return []

    patient_ids = [patient["id"] for patient in patients_resp.data]
    patient_names = {patient["id"]: _patient_label(patient) for patient in patients_resp.data}

    alerts_resp = (
        supabase.table("clinical_alerts")
        .select("id, patient_id, source_type, severity, created_at, status")
        .in_("patient_id", patient_ids)
        .eq("status", "open")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
    sorted_alerts = sorted(
        alerts_resp.data or [],
        key=lambda alert: severity_order.get(alert.get("severity", "low"), 3),
    )

    return [
        AlertItem(
            id=alert["id"],
            patient_id=alert["patient_id"],
            patient_name=patient_names.get(alert["patient_id"]),
            alert_type=alert.get("source_type", "clinical_alert"),
            severity=alert.get("severity", "low"),
            message=_alert_message(alert),
            created_at=alert.get("created_at", ""),
            status=alert.get("status", "open"),
        )
        for alert in sorted_alerts
    ]


@router.put("/alerts/{alert_id}/resolve", status_code=status.HTTP_200_OK)
async def resolve_alert(
    alert_id: str,
    doctor_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token),
):
    alert_resp = (
        supabase.table("clinical_alerts")
        .select("id, patient_id")
        .eq("id", alert_id)
        .single()
        .execute()
    )

    if not alert_resp.data:
        raise HTTPException(status_code=404, detail="Alerta nao encontrado.")

    _get_patient_or_403(alert_resp.data["patient_id"], doctor_id)

    supabase.table("clinical_alerts").update(
        {
            "status": "resolved",
            "resolved_at": datetime.utcnow().isoformat(),
            "resolved_by": doctor_id,
        }
    ).eq("id", alert_id).execute()

    return {"message": "Alerta resolvido com sucesso."}


@router.get("/patients/{patient_id}/modules")
async def get_patient_modules(
    patient_id: str,
    doctor_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token),
):
    _get_patient_or_403(patient_id, doctor_id)

    modules_resp = (
        supabase.table("patient_modules")
        .select("module_id, is_enabled, config, modules(code, display_name, description)")
        .eq("patient_id", patient_id)
        .execute()
    )

    return modules_resp.data or []


@router.put("/patients/{patient_id}/modules", status_code=status.HTTP_200_OK)
async def toggle_patient_module(
    patient_id: str,
    toggle: ModuleToggle,
    doctor_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token),
):
    _get_patient_or_403(patient_id, doctor_id)

    module_resp = (
        supabase.table("modules")
        .select("id")
        .eq("code", toggle.module_code)
        .single()
        .execute()
    )

    if not module_resp.data:
        raise HTTPException(status_code=404, detail=f"Modulo '{toggle.module_code}' nao encontrado.")

    module_id = module_resp.data["id"]
    existing = (
        supabase.table("patient_modules")
        .select("id")
        .eq("patient_id", patient_id)
        .eq("module_id", module_id)
        .single()
        .execute()
    )

    payload = {"is_enabled": toggle.is_active}
    if existing.data:
        supabase.table("patient_modules").update(payload).eq("id", existing.data["id"]).execute()
    else:
        supabase.table("patient_modules").insert(
            {"patient_id": patient_id, "module_id": module_id, **payload}
        ).execute()

    action = "ativado" if toggle.is_active else "desativado"
    return {"message": f"Modulo '{toggle.module_code}' {action} com sucesso."}
