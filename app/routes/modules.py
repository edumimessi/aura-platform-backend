"""
modules.py - Rotas para os modulos adicionais do MVP.

Centraliza a criacao/listagem de registros para reduzir repeticao e manter
os payloads alinhados ao schema SQL.
"""

from datetime import datetime, timedelta
from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_user_id
from app.database import supabase
from app.models import (
    DietRecordCreate,
    DietRecordResponse,
    ExerciseRecordCreate,
    ExerciseRecordResponse,
    MedicationRecordCreate,
    MedicationRecordResponse,
    MeditationRecordCreate,
    MeditationRecordResponse,
    SleepRecordCreate,
    SleepRecordResponse,
    SymptomRecordCreate,
    SymptomRecordResponse,
)

router = APIRouter(prefix="/api/modules", tags=["Modules"])


def verify_patient_access(patient_id: str, user_id: str) -> dict:
    """Verifica se o usuario autenticado tem acesso ao paciente."""
    try:
        patient = (
            supabase.table("patients")
            .select("doctor_id, auth_user_id")
            .eq("id", patient_id)
            .single()
            .execute()
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Paciente nao encontrado")

    if not patient.data:
        raise HTTPException(status_code=404, detail="Paciente nao encontrado")

    is_doctor = patient.data["doctor_id"] == user_id
    is_patient = patient.data["auth_user_id"] == user_id

    if not (is_doctor or is_patient):
        raise HTTPException(status_code=403, detail="Acesso negado")

    return patient.data


def get_patient_id_from_user(user_id: str) -> str:
    """Obtem o patient_id a partir do auth_user_id do JWT."""
    try:
        patient = (
            supabase.table("patients")
            .select("id")
            .eq("auth_user_id", user_id)
            .single()
            .execute()
        )
        if patient.data:
            return patient.data["id"]
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="Paciente nao encontrado para este usuario")


def _json_ready(data: dict) -> dict:
    """Converte tipos Python para valores aceitos pelo PostgREST."""
    normalized = {}
    for key, value in data.items():
        if value is None:
            continue
        if hasattr(value, "isoformat"):
            normalized[key] = value.isoformat()
        else:
            normalized[key] = value
    return normalized


def _create_record(table: str, record, patient_id: str) -> dict:
    record_data = _json_ready(record.model_dump(exclude_none=True))
    record_data["id"] = str(uuid.uuid4())
    record_data["patient_id"] = patient_id

    try:
        response = supabase.table(table).insert(record_data).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar registro: {str(e)}")

    if not response.data:
        raise HTTPException(status_code=500, detail="Erro ao salvar registro")

    return response.data[0]


def _list_records(table: str, patient_id: str, date_column: str, days: int) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    cutoff_value = cutoff.date().isoformat() if date_column == "record_date" else cutoff.isoformat()

    try:
        response = (
            supabase.table(table)
            .select("*")
            .eq("patient_id", patient_id)
            .gte(date_column, cutoff_value)
            .order(date_column, desc=True)
            .execute()
        )
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar registros: {str(e)}")


# ============================================================
# SLEEP RECORDS
# ============================================================
@router.post("/sleep", response_model=SleepRecordResponse, status_code=201)
async def create_sleep_record(record: SleepRecordCreate, user_id: str = Depends(get_user_id)):
    return _create_record("sleep_records", record, get_patient_id_from_user(user_id))


@router.get("/sleep/{patient_id}", response_model=List[SleepRecordResponse])
async def get_sleep_records(patient_id: str, days: int = 30, user_id: str = Depends(get_user_id)):
    verify_patient_access(patient_id, user_id)
    return _list_records("sleep_records", patient_id, "record_date", days)


# ============================================================
# EXERCISE RECORDS
# ============================================================
@router.post("/exercise", response_model=ExerciseRecordResponse, status_code=201)
async def create_exercise_record(record: ExerciseRecordCreate, user_id: str = Depends(get_user_id)):
    return _create_record("exercise_records", record, get_patient_id_from_user(user_id))


@router.get("/exercise/{patient_id}", response_model=List[ExerciseRecordResponse])
async def get_exercise_records(patient_id: str, days: int = 30, user_id: str = Depends(get_user_id)):
    verify_patient_access(patient_id, user_id)
    return _list_records("exercise_records", patient_id, "record_date", days)


# ============================================================
# MEDITATION RECORDS
# ============================================================
@router.post("/meditation", response_model=MeditationRecordResponse, status_code=201)
async def create_meditation_record(record: MeditationRecordCreate, user_id: str = Depends(get_user_id)):
    return _create_record("meditation_records", record, get_patient_id_from_user(user_id))


@router.get("/meditation/{patient_id}", response_model=List[MeditationRecordResponse])
async def get_meditation_records(patient_id: str, days: int = 30, user_id: str = Depends(get_user_id)):
    verify_patient_access(patient_id, user_id)
    return _list_records("meditation_records", patient_id, "record_date", days)


# ============================================================
# DIET RECORDS
# ============================================================
@router.post("/diet", response_model=DietRecordResponse, status_code=201)
async def create_diet_record(record: DietRecordCreate, user_id: str = Depends(get_user_id)):
    return _create_record("diet_records", record, get_patient_id_from_user(user_id))


@router.get("/diet/{patient_id}", response_model=List[DietRecordResponse])
async def get_diet_records(patient_id: str, days: int = 30, user_id: str = Depends(get_user_id)):
    verify_patient_access(patient_id, user_id)
    return _list_records("diet_records", patient_id, "record_date", days)


# ============================================================
# CUSTOM SYMPTOMS
# ============================================================
@router.post("/symptoms", response_model=SymptomRecordResponse, status_code=201)
async def create_symptom_record(record: SymptomRecordCreate, user_id: str = Depends(get_user_id)):
    return _create_record("symptom_records", record, get_patient_id_from_user(user_id))


@router.get("/symptoms/{patient_id}", response_model=List[SymptomRecordResponse])
async def get_symptom_records(patient_id: str, days: int = 30, user_id: str = Depends(get_user_id)):
    verify_patient_access(patient_id, user_id)
    return _list_records("symptom_records", patient_id, "record_date", days)


# ============================================================
# MEDICATION RECORDS
# ============================================================
@router.post("/medications", response_model=MedicationRecordResponse, status_code=201)
async def create_medication_record(record: MedicationRecordCreate, user_id: str = Depends(get_user_id)):
    return _create_record("medication_records", record, get_patient_id_from_user(user_id))


@router.get("/medications/{patient_id}", response_model=List[MedicationRecordResponse])
async def get_medication_records(patient_id: str, days: int = 30, user_id: str = Depends(get_user_id)):
    verify_patient_access(patient_id, user_id)
    return _list_records("medication_records", patient_id, "scheduled_at", days)
