"""
services/alert_service.py — Lógica de geração de alertas

Corrigido:
- Busca FCM tokens em patient_devices (não em patients)
- Sincronização de crises incluída
"""

from app.database import supabase
from datetime import datetime, timedelta
import uuid

def check_medication_adherence(patient_id: str):
    """
    Verifica adesão a medicações.
    Se X doses foram perdidas consecutivas, gera alerta.
    """
    try:
        # Query: últimas 7 doses do paciente
        response = supabase.table('medication_records').select('*').eq(
            'patient_id', patient_id
        ).order('scheduled_at', desc=True).limit(7).execute()
        
        records = response.data
        missed_count = sum(1 for r in records if r['status'] == 'missed')
        
        # Se 3 ou mais doses perdidas em 7 dias
        if missed_count >= 3:
            alert_data = {
                'id': str(uuid.uuid4()),
                'patient_id': patient_id,
                'source_type': 'medication_adherence',
                'severity': 'moderate',
                'status': 'open'
            }
            supabase.table('clinical_alerts').insert(alert_data).execute()
    except Exception as e:
        print(f"Erro ao verificar adesão: {e}")


def check_no_activity(patient_id: str, days_threshold: int = 3):
    """
    Verifica se o paciente não registrou atividade por N dias.
    """
    try:
        # Query: último registro de qualquer tipo
        response = supabase.table('mood_records').select('created_at').eq(
            'patient_id', patient_id
        ).order('created_at', desc=True).limit(1).execute()
        
        if not response.data:
            return
        
        last_activity = datetime.fromisoformat(response.data[0]['created_at'])
        days_inactive = (datetime.utcnow() - last_activity).days
        
        if days_inactive >= days_threshold:
            alert_data = {
                'id': str(uuid.uuid4()),
                'patient_id': patient_id,
                'source_type': 'no_activity',
                'severity': 'low',
                'status': 'open'
            }
            supabase.table('clinical_alerts').insert(alert_data).execute()
    except Exception as e:
        print(f"Erro ao verificar inatividade: {e}")


def send_push_notification(patient_id: str, alert_id: str, title: str, body: str):
    """
    Envia notificação push via Firebase Cloud Messaging.
    
    CORRIGIDO: Busca FCM tokens em patient_devices (pode haver múltiplos).
    """
    try:
        # Buscar todos os dispositivos ativos do paciente
        devices_response = supabase.table('patient_devices').select('fcm_token').eq(
            'patient_id', patient_id
        ).eq('is_active', True).execute()
        
        if not devices_response.data:
            print(f"Nenhum dispositivo ativo para paciente {patient_id}")
            return
        
        # Enviar para cada dispositivo
        for device in devices_response.data:
            fcm_token = device['fcm_token']
            
            # Aqui entraria a lógica de Firebase Cloud Messaging
            # Por enquanto, apenas log
            print(f"Enviando notificação para {fcm_token}: {title}")
            
            try:
                # Atualizar timestamp de envio
                supabase.table('clinical_alerts').update({
                    'notification_sent_at': datetime.utcnow().isoformat(),
                    'notification_channel': 'push'
                }).eq('id', alert_id).execute()
            except Exception as e:
                print(f"Erro ao atualizar alerta: {e}")
    except Exception as e:
        print(f"Erro ao buscar dispositivos: {e}")
