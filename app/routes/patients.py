"""
routes/patients.py - Endpoints para o fluxo inicial de pacientes.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_optional_user_id, get_user_id
from app.database import supabase
from app.models import PatientCreate, PatientResponse

router = APIRouter(prefix="/patients", tags=["patients"])

PATIENT_COLUMNS = (
    "id, auth_user_id, doctor_id, birth_date, gender, "
    "is_active, anonymized_at, created_at, updated_at"
)


@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    patient: PatientCreate,
    authenticated_user_id: str | None = Depends(get_optional_user_id),
):
    """
    Cria um paciente.

    Observação de segurança:
    doctor_id é aceito no corpo apenas temporariamente para MVP/dev.
    Em produção, doctor_id deve vir do JWT do médico autenticado.
    """
    patient_data = patient.model_dump(exclude_none=True, mode="json")

    if authenticated_user_id:
        patient_data["doctor_id"] = authenticated_user_id
    elif "doctor_id" not in patient_data:
        raise HTTPException(
            status_code=401,
            detail="Autenticação obrigatória ou doctor_id temporário para dev.",
        )

    try:
        response = (
            supabase.table("patients")
            .insert(patient_data)
            .select(PATIENT_COLUMNS)
            .execute()
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Não foi possível criar o paciente.",
        )

    if not response.data:
        raise HTTPException(
            status_code=500,
            detail="Não foi possível criar o paciente.",
        )

    return response.data[0]


@router.get("", response_model=list[PatientResponse])
async def list_patients(
    doctor_id: str = Depends(get_user_id),
):
    """
    Lista pacientes ativos do médico autenticado.

    LGPD: filtra obrigatoriamente por doctor_id extraído do JWT.
    O médico só vê seus próprios pacientes — nunca os de outro médico.
    A SERVICE_KEY bypassa RLS, então o filtro deve ser feito aqui no código.
    """
    try:
        response = (
            supabase.table("patients")
            .select(PATIENT_COLUMNS)
            .eq("is_active", True)
            .eq("doctor_id", doctor_id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Não foi possível listar os pacientes.",
        )

    return response.data or []
