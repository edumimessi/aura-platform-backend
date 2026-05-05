"""
consent.py — Endpoints de Consentimento LGPD

Gerencia o registro e verificação de consentimentos dos pacientes.
Base legal: LGPD Art. 7º, inciso I e Art. 11, inciso II, alínea "f".

Endpoints:
    POST /api/consent          — Registrar aceite de consentimento
    GET  /api/consent/status   — Verificar se há consentimento ativo
    POST /api/consent/revoke   — Revogar consentimento
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.auth import verify_supabase_token, get_user_id
from app.database import supabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/consent", tags=["Consentimento LGPD"])


# ============================================================
# MODELS
# ============================================================

class ConsentCreate(BaseModel):
    """Dados para registrar um consentimento."""
    consent_type: str = "data_processing"
    version: str = "1.0"  # app_version no schema
    accepted: bool


class ConsentResponse(BaseModel):
    """Resposta após registrar consentimento."""
    id: str
    consent_type: str
    granted: bool
    granted_at: str
    message: str


class ConsentStatusResponse(BaseModel):
    """Status do consentimento do usuário."""
    has_active_consent: bool
    consent_type: Optional[str] = None
    granted_at: Optional[str] = None


class ConsentRevokeRequest(BaseModel):
    """Dados para revogar consentimento."""
    reason: Optional[str] = None


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def register_consent(
    consent: ConsentCreate,
    user_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token)
):
    """
    Registra o aceite do consentimento LGPD.

    Busca o patient_id pelo auth_user_id do JWT e registra
    o consentimento na tabela patient_consents.
    """
    if not consent.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O consentimento precisa ser aceito para continuar."
        )

    # Buscar patient_id pelo auth_user_id
    patient_resp = supabase.table("patients") \
        .select("id") \
        .eq("auth_user_id", user_id) \
        .single() \
        .execute()

    if not patient_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente não encontrado para este usuário."
        )

    patient_id = patient_resp.data["id"]

    # Verificar se já existe consentimento ativo para este tipo
    # O schema é imutável (nunca update) — verificamos se há linha com granted=True e sem revoked_at
    existing = supabase.table("patient_consents") \
        .select("id, granted_at") \
        .eq("patient_id", patient_id) \
        .eq("consent_type", consent.consent_type) \
        .eq("granted", True) \
        .is_("revoked_at", "null") \
        .order("granted_at", desc=True) \
        .limit(1) \
        .execute()

    if existing.data:
        # Já tem consentimento ativo — retornar sem duplicar
        existing_consent = existing.data[0]
        return ConsentResponse(
            id=existing_consent["id"],
            consent_type=consent.consent_type,
            granted=True,
            granted_at=existing_consent.get("granted_at", datetime.utcnow().isoformat()),
            message="Consentimento já registrado anteriormente."
        )

    # Registrar novo consentimento — schema é append-only (nunca update)
    now = datetime.utcnow().isoformat()
    insert_data = {
        "patient_id": patient_id,
        "consent_type": consent.consent_type,
        "granted": True,
        "granted_at": now,
        "app_version": consent.version,
    }

    result = supabase.table("patient_consents").insert(insert_data).execute()

    if not result.data:
        logger.error(f"Erro ao registrar consentimento para patient_id={patient_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao registrar consentimento."
        )

    logger.info(f"Consentimento registrado: patient_id={patient_id}, version={consent.version}")

    return ConsentResponse(
        id=result.data[0]["id"],
        consent_type=consent.consent_type,
        granted=True,
        granted_at=now,
        message="Consentimento registrado com sucesso."
    )


@router.get("/status", response_model=ConsentStatusResponse)
async def get_consent_status(
    user_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token)
):
    """
    Verifica se o usuário autenticado tem consentimento ativo.

    Usado pelo app no _AuthGate para decidir se mostra
    a tela de consentimento ou vai direto para a home.
    """
    # Buscar patient_id
    patient_resp = supabase.table("patients") \
        .select("id") \
        .eq("auth_user_id", user_id) \
        .single() \
        .execute()

    if not patient_resp.data:
        # Usuário sem cadastro de paciente — pode ser médico ou novo usuário
        # Não bloquear, retornar sem consentimento ativo
        return ConsentStatusResponse(has_active_consent=False)

    patient_id = patient_resp.data["id"]

    # Buscar consentimento ativo — granted=True e sem revoked_at
    consent_resp = supabase.table("patient_consents") \
        .select("consent_type, granted_at") \
        .eq("patient_id", patient_id) \
        .eq("consent_type", "data_processing") \
        .eq("granted", True) \
        .is_("revoked_at", "null") \
        .order("granted_at", desc=True) \
        .limit(1) \
        .execute()

    if not consent_resp.data:
        return ConsentStatusResponse(has_active_consent=False)

    consent_data = consent_resp.data[0]
    return ConsentStatusResponse(
        has_active_consent=True,
        consent_type=consent_data["consent_type"],
        granted_at=consent_data["granted_at"],
    )


@router.post("/revoke", status_code=status.HTTP_200_OK)
async def revoke_consent(
    revoke: ConsentRevokeRequest,
    user_id: str = Depends(get_user_id),
    _token: dict = Depends(verify_supabase_token)
):
    """
    Revoga o consentimento do paciente.

    Direito garantido pela LGPD Art. 8º, §5º.
    Não exclui os dados — apenas marca o consentimento como inativo.
    A exclusão de dados deve ser solicitada separadamente ao médico.
    """
    patient_resp = supabase.table("patients") \
        .select("id") \
        .eq("auth_user_id", user_id) \
        .single() \
        .execute()

    if not patient_resp.data:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")

    patient_id = patient_resp.data["id"]

    # Inserir nova linha de revogação — schema é append-only
    # A revogação é registrada como granted=False com revoked_at preenchido
    supabase.table("patient_consents").insert({
        "patient_id": patient_id,
        "consent_type": "data_processing",
        "granted": False,
        "granted_at": datetime.utcnow().isoformat(),
        "revoked_at": datetime.utcnow().isoformat(),
    }).execute()

    logger.info(f"Consentimento revogado: patient_id={patient_id}, reason={revoke.reason}")

    return {
        "message": "Consentimento revogado com sucesso. "
                   "Para solicitar exclusão dos seus dados, entre em contato com o consultório."
    }
