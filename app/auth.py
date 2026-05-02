"""
auth.py — Autenticação com Supabase JWT

IMPORTANTE: Este arquivo NÃO gera tokens. Apenas valida tokens
emitidos pelo Supabase Auth.

Fluxo:
1. Flutter faz login via Supabase Auth.
2. Supabase retorna JWT (gerado por eles).
3. Flutter envia esse JWT no header Authorization.
4. FastAPI valida o JWT usando a chave secreta do Supabase.
5. Se válido, extrai user_id e processa a requisição.
"""

import os
from dotenv import load_dotenv
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

# Carrega o .env ANTES de qualquer os.getenv()
# Sem isso, as variáveis de ambiente não estão disponíveis ainda.
load_dotenv()

security = HTTPBearer()

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

if not SUPABASE_JWT_SECRET:
    raise ValueError(
        "SUPABASE_JWT_SECRET é obrigatório. "
        "Verifique se o arquivo .env existe na raiz do projeto "
        "e contém a variável SUPABASE_JWT_SECRET preenchida."
    )


async def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Valida o JWT emitido pelo Supabase Auth.

    Retorna o payload completo (contém user_id, role, etc).

    NÃO cria tokens — apenas verifica os que chegam.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            # Supabase emite tokens com audience "authenticated"
            options={"verify_aud": False}
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token sem user_id")
        return payload  # retorna payload completo
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {str(e)}")


def get_user_id(payload: dict = Depends(verify_supabase_token)) -> str:
    """Extrai o user_id do payload do JWT."""
    return payload["sub"]


def get_user_role(payload: dict = Depends(verify_supabase_token)) -> str:
    """Extrai a role do payload do JWT."""
    return payload.get("app_metadata", {}).get("role", "patient")
