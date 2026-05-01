"""
routes/logs.py — Endpoints para registros diários

Corrigido:
- Usa verify_supabase_token em vez de create_access_token
- Valida permissões manualmente (médico ou paciente)
- Aplica regras clínicas (alerta se humor crítico)
"""

from fastapi import APIRouter, Depends, HTTPException
from app.models import (
    MoodRecordCreate, MoodRecordResponse,
    CrisisRecordCreate, CrisisRecordResponse,
    MedicationRecordCreate, MedicationRecordResponse
)
from app.auth import verify_supabase_token, get_user_id
from app.database import supabase
from datetime import date
import uuid

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.post("/mood", response_model=MoodRecordResponse, status_code=201)
async def create_mood_record(
    log: MoodRecordCreate,
    user_id: str = Depends(get_user_id)
):
    """
    Cria um registro de humor.
    
    Fluxo:
    1. Valida o token JWT do Supabase (user_id extraído).
    2. Verifica se o usuário é paciente e se o paciente existe.
    3. Aplica regra clínica: se humor <= 3, gera alerta.
    4. Salva no banco.
    5. Retorna o registro criado.
    """
    
    # Passo 1: Verificar se o paciente existe e pertence ao usuário
    try:
        patient_response = supabase.table('patients').select('id, doctor_id').eq(
            'auth_user_id', user_id
        ).single().execute()
    except Exception as e:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    
    if not patient_response.data:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    
    patient_id = patient_response.data['id']
    
    # Passo 2: Salvar o registro de humor
    record_id = str(uuid.uuid4())
    record_data = {
        'id': record_id,
        'patient_id': patient_id,
        'score': log.score,
        'emotions': log.emotions,
        'notes': log.notes,
        'record_date': str(log.record_date),
        'source': 'manual'
    }
    
    try:
        response = supabase.table('mood_records').insert(record_data).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar registro: {str(e)}")
    
    if not response.data:
        raise HTTPException(status_code=500, detail="Erro ao salvar registro")
    
    # Passo 3: Aplicar regra clínica — alerta se humor crítico
    if log.score <= 3:
        alert_data = {
            'id': str(uuid.uuid4()),
            'patient_id': patient_id,
            'source_type': 'mood_critical',
            'source_record_id': record_id,
            'severity': 'high' if log.score <= 2 else 'moderate',
            'status': 'open'
        }
        try:
            supabase.table('clinical_alerts').insert(alert_data).execute()
        except Exception as e:
            # Log mas não falha — o registro de humor foi salvo
            print(f"Aviso: erro ao criar alerta: {e}")
    
    return response.data[0]


@router.get("/mood/{patient_id}", response_model=list[MoodRecordResponse])
async def get_mood_records(
    patient_id: str,
    days: int = 30,
    user_id: str = Depends(get_user_id)
):
    """
    Retorna registros de humor dos últimos N dias.
    
    Segurança: Verifica se o user_id é o médico responsável ou o próprio paciente.
    """
    
    # Verificar permissão: é médico do paciente ou é o paciente?
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
    
    # Query com filtro de data
    try:
        response = supabase.table('mood_records').select('*').eq(
            'patient_id', patient_id
        ).gte(
            'record_date', f"now() - interval '{days} days'"
        ).order('record_date', desc=True).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar registros: {str(e)}")
    
    return response.data


@router.post("/crisis", response_model=CrisisRecordResponse, status_code=201)
async def create_crisis_record(
    record: CrisisRecordCreate,
    user_id: str = Depends(get_user_id)
):
    """
    Cria um registro de crise.
    
    CRÍTICO: Gera alerta imediato ao médico, especialmente se ideação suicida.
    """
    
    # Verificar paciente
    try:
        patient_response = supabase.table('patients').select('id, doctor_id').eq(
            'auth_user_id', user_id
        ).single().execute()
    except Exception:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    
    patient_id = patient_response.data['id']
    doctor_id = patient_response.data['doctor_id']
    
    # Salvar crise
    crisis_id = str(uuid.uuid4())
    crisis_data = {
        'id': crisis_id,
        'patient_id': patient_id,
        'intensity': record.intensity,
        'crisis_types': record.crisis_types,
        'has_suicidal_ideation': record.has_suicidal_ideation,
        'coping_used': record.coping_used,
        'notes': record.notes
    }
    
    try:
        response = supabase.table('crisis_records').insert(crisis_data).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar crise: {str(e)}")
    
    # Gerar alerta CRÍTICO
    severity = 'critical' if record.has_suicidal_ideation else 'high'
    alert_data = {
        'id': str(uuid.uuid4()),
        'patient_id': patient_id,
        'source_type': 'crisis_record',
        'source_record_id': crisis_id,
        'severity': severity,
        'status': 'open'
    }
    
    try:
        supabase.table('clinical_alerts').insert(alert_data).execute()
    except Exception as e:
        print(f"Aviso: erro ao criar alerta de crise: {e}")
    
    return response.data[0]
