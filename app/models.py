"""
models.py — Validação de dados com Pydantic v2

Usa Literal em vez de regex para enums — mais legível e seguro.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Literal
from datetime import date, datetime
from uuid import UUID


# ============================================================
# PATIENTS
# ============================================================
class PatientCreate(BaseModel):
    """Modelo para criar um paciente no MVP."""

    model_config = ConfigDict(extra="forbid")

    # Temporário para MVP/dev:
    # em produção, doctor_id deve vir do JWT do médico autenticado,
    # nunca do corpo da requisição.
    doctor_id: UUID
    auth_user_id: Optional[UUID] = None
    birth_date: Optional[date] = None
    gender: Optional[
        Literal["male", "female", "non_binary", "prefer_not_to_say"]
    ] = None


class PatientResponse(BaseModel):
    """Modelo de resposta para paciente."""

    id: UUID
    auth_user_id: Optional[UUID]
    doctor_id: UUID
    birth_date: Optional[date]
    gender: Optional[str]
    is_active: bool
    anonymized_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================================
# MOOD RECORDS
# ============================================================
class MoodRecordCreate(BaseModel):
    """Modelo para criar um registro de humor."""
    score: int = Field(..., ge=1, le=10, description="Escala de humor 1-10")
    emotions: Optional[List[str]] = None
    notes: Optional[str] = Field(None, max_length=500)
    record_date: date = Field(default_factory=date.today)


class MoodRecordResponse(BaseModel):
    """Modelo de resposta para registro de humor."""
    id: str
    patient_id: str
    score: int
    emotions: Optional[List[str]]
    notes: Optional[str]
    record_date: date
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# MEDICATION RECORDS
# ============================================================
class MedicationRecordCreate(BaseModel):
    """Modelo para criar um registro de medicação."""
    medication_id: str
    status: Literal['taken', 'missed', 'delayed', 'skipped_intentional', 'pending']
    skip_reason: Optional[str] = None
    taken_at: Optional[datetime] = None


class MedicationRecordResponse(BaseModel):
    """Modelo de resposta para registro de medicação."""
    id: str
    patient_id: str
    medication_id: str
    status: str
    taken_at: Optional[datetime]
    skip_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# CRISIS RECORDS
# ============================================================
class CrisisRecordCreate(BaseModel):
    """Modelo para criar um registro de crise."""
    intensity: int = Field(..., ge=1, le=10)
    crisis_types: List[str]
    has_suicidal_ideation: bool = False
    coping_used: Optional[List[str]] = None
    notes: Optional[str] = None


class CrisisRecordResponse(BaseModel):
    """Modelo de resposta para registro de crise."""
    id: str
    patient_id: str
    intensity: int
    crisis_types: List[str]
    has_suicidal_ideation: bool
    coping_used: Optional[List[str]]
    notes: Optional[str]
    occurred_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# DEVICE REGISTRATION
# ============================================================
class DeviceRegisterRequest(BaseModel):
    """Modelo para registrar um dispositivo (FCM token)."""
    fcm_token: str
    platform: Literal['ios', 'android']
    device_name: Optional[str] = None


class DeviceRegisterResponse(BaseModel):
    """Modelo de resposta para registro de dispositivo."""
    id: str
    fcm_token: str
    platform: str
    device_name: Optional[str]
    registered_at: datetime

    class Config:
        from_attributes = True
