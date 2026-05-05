"""
models.py — Validação de dados com Pydantic v2

Usa Literal em vez de regex para enums — mais legível e seguro.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Literal
from datetime import date, datetime, time
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
    doctor_id: Optional[UUID] = None
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
    # Valores devem corresponder ao CHECK constraint do banco:
    # taken | missed | delayed | skipped | pending
    status: Literal['taken', 'missed', 'delayed', 'skipped', 'pending']
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

# ============================================================
# SLEEP RECORDS
# ============================================================
class SleepRecordCreate(BaseModel):
    """Modelo para criar um registro de sono."""
    record_date: date = Field(default_factory=date.today)
    sleep_time: Optional[time] = None
    wake_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    quality_score: Optional[int] = Field(None, ge=1, le=5)
    had_nightmares: bool = False
    had_insomnia: bool = False
    used_sleep_medication: bool = False
    notes: Optional[str] = None

class SleepRecordResponse(BaseModel):
    """Modelo de resposta para registro de sono."""
    id: str
    patient_id: str
    record_date: date
    sleep_time: Optional[time]
    wake_time: Optional[time]
    duration_minutes: Optional[int]
    quality_score: Optional[int]
    had_nightmares: bool
    had_insomnia: bool
    used_sleep_medication: bool
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================
# EXERCISE RECORDS
# ============================================================
class ExerciseRecordCreate(BaseModel):
    """Modelo para criar um registro de exercício."""
    record_date: date = Field(default_factory=date.today)
    exercise_type: Optional[str] = None
    duration_minutes: Optional[int] = None
    intensity: Optional[Literal['light', 'moderate', 'intense']] = None
    mood_after: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None

class ExerciseRecordResponse(BaseModel):
    """Modelo de resposta para registro de exercício."""
    id: str
    patient_id: str
    record_date: date
    exercise_type: Optional[str]
    duration_minutes: Optional[int]
    intensity: Optional[str]
    mood_after: Optional[int]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================
# MEDITATION RECORDS
# ============================================================
class MeditationRecordCreate(BaseModel):
    """Modelo para criar um registro de meditação."""
    record_date: date = Field(default_factory=date.today)
    duration_minutes: int
    technique: Optional[str] = None
    focus_score: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None

class MeditationRecordResponse(BaseModel):
    """Modelo de resposta para registro de meditação."""
    id: str
    patient_id: str
    record_date: date
    duration_minutes: int
    technique: Optional[str]
    focus_score: Optional[int]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================
# DIET RECORDS
# ============================================================
class DietRecordCreate(BaseModel):
    """Modelo para criar um registro de dieta."""
    record_date: date = Field(default_factory=date.today)
    quality_score: Optional[int] = Field(None, ge=1, le=5)
    water_intake_ok: Optional[bool] = None
    skipped_meals: Optional[int] = None
    had_binge: Optional[bool] = None
    had_restriction: Optional[bool] = None
    notes: Optional[str] = None

class DietRecordResponse(BaseModel):
    """Modelo de resposta para registro de dieta."""
    id: str
    patient_id: str
    record_date: date
    quality_score: Optional[int]
    water_intake_ok: Optional[bool]
    skipped_meals: Optional[int]
    had_binge: Optional[bool]
    had_restriction: Optional[bool]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================
# CUSTOM SYMPTOMS
# ============================================================
class SymptomRecordCreate(BaseModel):
    """Modelo para criar um registro de sintoma customizável."""
    symptom_id: str
    record_date: date = Field(default_factory=date.today)
    numeric_value: Optional[float] = None
    boolean_value: Optional[bool] = None
    frequency_value: Optional[Literal['never', 'sometimes', 'often', 'always']] = None
    notes: Optional[str] = None

class SymptomRecordResponse(BaseModel):
    """Modelo de resposta para registro de sintoma customizável."""
    id: str
    patient_id: str
    symptom_id: str
    record_date: date
    recorded_at: datetime
    numeric_value: Optional[float]
    boolean_value: Optional[bool]
    frequency_value: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
