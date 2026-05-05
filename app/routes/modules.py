"""
modules.py — Rotas para os módulos adicionais do MVP (Sono, Exercício, Meditação, Dieta, Sintomas, Medicação)
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from datetime import datetime, timedelta
import uuid

from app.database import supabase
from app.auth import get_user_id
from app.models import (
    SleepRecordCreate, SleepRecordResponse,
    ExerciseRecordCreate, ExerciseRecordResponse,
    MeditationRecordCreate, MeditationRecordResponse,
    DietRecordCreate, DietRecordResponse,
    SymptomRecordCreate, SymptomRecordResponse,
    MedicationRecordCreate, MedicationRecordResponse
)

router = APIRouter(
    prefix="/api/modules",
    tags=["Modules"]
)

def verify_patient_access(patient_id: str, user_id: str):
    """Verifica se o usuário autenticado tem acesso ao paciente."""
    try:
        patient = supabase.table('patients').select('doctor_id, auth_user_id').eq(
            'id', patient_id
        ).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    
    if not patient.data:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    
    is_doctor = patient.data['doctor_id'] == user_id
    is_patient = patient.data['auth_user_id'] == user_id
    
    if not (is_doctor or is_patient):
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    return patient.data

def get_patient_id_from_user(user_id: str) -> str:
    """Obtém o patient_id a partir do auth_user_id do JWT."""
    try:
        patient = supabase.table('patients').select('id').eq(
            'auth_user_id', user_id
        ).single().execute()
        return patient.data['id']
    except Exception:
        raise HTTPException(status_code=404, detail="Paciente não encontrado para este usuário")

# ============================================================
# SLEEP RECORDS
# ============================================================
@router.post("/sleep", response_model=SleepRecordResponse, status_code=201)
async def create_sleep_record(
    record: SleepRecordCreate,
    user_id: str = Depends(get_user_id)
):
    patient_id = get_patient_id_from_user(user_id)
    
    record_data = record.model_dump(exclude_none=True)
    record_data['id'] = str(uuid.uuid4())
    record_data['patient_id'] = patient_id
    record_data['record_date'] = str(record.record_date)
    
    if 'sleep_time' in record_data:
        record_data['sleep_time'] = str(record_data['sleep_time'])
    if 'wake_time' in record_data:
        record_data['wake_time'] = str(record_data['wake_time'])
        
    try:
        response = supabase.table('sleep_records').insert(record_data).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar registro de sono: {str(e)}")

@router.get("/sleep/{patient_id}", response_model=List[SleepRecordResponse])
async def get_sleep_records(
    patient_id: str,
    days: int = 30,
    user_id: str = Depends(get_user_id)
):
    verify_patient_access(patient_id, user_id)
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
    
    try:
        response = supabase.table('sleep_records').select('*').eq(
            'patient_id', patient_id
        ).gte('record_date', cutoff_date).order('record_date', desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar registros: {str(e)}")

# ============================================================
# EXERCISE RECORDS
# ============================================================
@router.post("/exercise", response_model=ExerciseRecordResponse, status_code=201)
async def create_exercise_record(
    record: ExerciseRecordCreate,
    user_id: str = Depends(get_user_id)
):
    patient_id = get_patient_id_from_user(user_id)
    
    record_data = record.model_dump(exclude_none=True)
    record_data['id'] = str(uuid.uuid4())
    record_data['patient_id'] = patient_id
    record_data['record_date'] = str(record.record_date)
        
    try:
        response = supabase.table('exercise_records').insert(record_data).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar registro de exercício: {str(e)}")

@router.get("/exercise/{patient_id}", response_model=List[ExerciseRecordResponse])
async def get_exercise_records(
    patient_id: str,
    days: int = 30,
    user_id: str = Depends(get_user_id)
):
    verify_patient_access(patient_id, user_id)
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
    
    try:
        response = supabase.table('exercise_records').select('*').eq(
            'patient_id', patient_id
        ).gte('record_date', cutoff_date).order('record_date', desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar registros: {str(e)}")

# ============================================================
# MEDITATION RECORDS
# ============================================================
@router.post("/meditation", response_model=MeditationRecordResponse, status_code=201)
async def create_meditation_record(
    record: MeditationRecordCreate,
    user_id: str = Depends(get_user_id)
):
    patient_id = get_patient_id_from_user(user_id)
    
    record_data = record.model_dump(exclude_none=True)
    record_data['id'] = str(uuid.uuid4())
    record_data['patient_id'] = patient_id
    record_data['record_date'] = str(record.record_date)
        
    try:
        response = supabase.table('meditation_records').insert(record_data).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar registro de meditação: {str(e)}")

@router.get("/meditation/{patient_id}", response_model=List[MeditationRecordResponse])
async def get_meditation_records(
    patient_id: str,
    days: int = 30,
    user_id: str = Depends(get_user_id)
):
    verify_patient_access(patient_id, user_id)
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
    
    try:
        response = supabase.table('meditation_records').select('*').eq(
            'patient_id', patient_id
        ).gte('record_date', cutoff_date).order('record_date', desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar registros: {str(e)}")

# ============================================================
# DIET RECORDS
# ============================================================
@router.post("/diet", response_model=DietRecordResponse, status_code=201)
async def create_diet_record(
    record: DietRecordCreate,
    user_id: str = Depends(get_user_id)
):
    patient_id = get_patient_id_from_user(user_id)
    
    record_data = record.model_dump(exclude_none=True)
    record_data['id'] = str(uuid.uuid4())
    record_data['patient_id'] = patient_id
    record_data['record_date'] = str(record.record_date)
        
    try:
        response = supabase.table('diet_records').insert(record_data).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar registro de dieta: {str(e)}")

@router.get("/diet/{patient_id}", response_model=List[DietRecordResponse])
async def get_diet_records(
    patient_id: str,
    days: int = 30,
    user_id: str = Depends(get_user_id)
):
    verify_patient_access(patient_id, user_id)
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
    
    try:
        response = supabase.table('diet_records').select('*').eq(
            'patient_id', patient_id
        ).gte('record_date', cutoff_date).order('record_date', desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar registros: {str(e)}")

# ============================================================
# CUSTOM SYMPTOMS
# ============================================================
@router.post("/symptoms", response_model=SymptomRecordResponse, status_code=201)
async def create_symptom_record(
    record: SymptomRecordCreate,
    user_id: str = Depends(get_user_id)
):
    patient_id = get_patient_id_from_user(user_id)
    
    record_data = record.model_dump(exclude_none=True)
    record_data['id'] = str(uuid.uuid4())
    record_data['patient_id'] = patient_id
    record_data['record_date'] = str(record.record_date)
        
    try:
        response = supabase.table('symptom_records').insert(record_data).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar registro de sintoma: {str(e)}")

@router.get("/symptoms/{patient_id}", response_model=List[SymptomRecordResponse])
async def get_symptom_records(
    patient_id: str,
    days: int = 30,
    user_id: str = Depends(get_user_id)
):
    verify_patient_access(patient_id, user_id)
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
    
    try:
        response = supabase.table('symptom_records').select('*').eq(
            'patient_id', patient_id
        ).gte('record_date', cutoff_date).order('record_date', desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar registros: {str(e)}")

# ============================================================
# MEDICATION RECORDS
# ============================================================
@router.post("/medications", response_model=MedicationRecordResponse, status_code=201)
async def create_medication_record(
    record: MedicationRecordCreate,
    user_id: str = Depends(get_user_id)
):
    patient_id = get_patient_id_from_user(user_id)
    
    record_data = record.model_dump(exclude_none=True)
    record_data['id'] = str(uuid.uuid4())
    record_data['patient_id'] = patient_id
    
    if 'taken_at' in record_data and record_data['taken_at']:
        record_data['taken_at'] = record_data['taken_at'].isoformat()
        
    try:
        response = supabase.table('medication_records').insert(record_data).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar registro de medicação: {str(e)}")

@router.get("/medications/{patient_id}", response_model=List[MedicationRecordResponse])
async def get_medication_records(
    patient_id: str,
    days: int = 30,
    user_id: str = Depends(get_user_id)
):
    verify_patient_access(patient_id, user_id)
    cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    try:
        response = supabase.table('medication_records').select('*').eq(
            'patient_id', patient_id
        ).gte('created_at', cutoff_date).order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar registros: {str(e)}")
