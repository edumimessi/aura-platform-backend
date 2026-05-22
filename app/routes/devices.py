"""
devices.py - Registro de dispositivos do paciente.

Recebe tokens FCM do app para uso futuro em notificacoes push.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_user_id
from app.database import supabase
from app.models import DeviceRegisterRequest, DeviceRegisterResponse

router = APIRouter(prefix="/api/devices", tags=["Devices"])


def _get_patient_id_from_user(user_id: str) -> str:
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


@router.post("/register", response_model=DeviceRegisterResponse, status_code=201)
async def register_device(
    device: DeviceRegisterRequest,
    user_id: str = Depends(get_user_id),
):
    patient_id = _get_patient_id_from_user(user_id)
    payload = device.model_dump(exclude_none=True)
    payload["patient_id"] = patient_id
    payload["is_active"] = True

    try:
        existing = (
            supabase.table("patient_devices")
            .select("id")
            .eq("fcm_token", device.fcm_token)
            .limit(1)
            .execute()
        )

        if existing.data:
            response = (
                supabase.table("patient_devices")
                .update(payload)
                .eq("id", existing.data[0]["id"])
                .execute()
            )
        else:
            response = supabase.table("patient_devices").insert(payload).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao registrar dispositivo: {str(e)}")

    if not response.data:
        raise HTTPException(status_code=500, detail="Erro ao registrar dispositivo")

    return response.data[0]
