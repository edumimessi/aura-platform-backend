"""
config.py — Configuração centralizada da aplicação AURA

Carrega variáveis de ambiente e valida configurações obrigatórias.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# SUPABASE
# ============================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # SERVICE_KEY, não anon
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

if not all([SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET]):
    raise ValueError(
        "Variáveis Supabase obrigatórias não configuradas. "
        "Verifique SUPABASE_URL, SUPABASE_SERVICE_KEY e SUPABASE_JWT_SECRET"
    )

# ============================================================
# FIREBASE
# ============================================================
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-credentials.json")

# ============================================================
# APP
# ============================================================
DEBUG = os.getenv("DEBUG", "True") == "True"
APP_NAME = "AURA API"
APP_VERSION = "0.2.0"
