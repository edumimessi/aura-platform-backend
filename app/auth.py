"""
auth.py - Autenticação com Supabase JWT.

Este arquivo não gera tokens. Ele apenas valida tokens emitidos
pelo Supabase Auth e expõe dependências FastAPI para extrair o usuário.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

# Carrega o .env antes de qualquer os.getenv().
load_dotenv()

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

if not SUPABASE_JWT_SECRET:
    raise ValueError(
        "SUPABASE_JWT_SECRET é obrigatório. "
        "Verifique se o arquivo .env existe na raiz do projeto "
        "e contém a variável SUPABASE_JWT_SECRET preenchida."
    )


def _decode_supabase_token(token: str) -> dict:
    """Decodifica o JWT do Supabase sem expor detalhes internos em erro."""
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            # Supabase emite tokens com audience "authenticated".
            options={"verify_aud": False},
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token sem user_id")

    return payload


async def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Valida o JWT emitido pelo Supabase Auth.

    Retorna o payload completo, incluindo o campo sub usado como user_id.
    """
    return _decode_supabase_token(credentials.credentials)


async def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
) -> Optional[str]:
    """
    Extrai o user_id quando Authorization: Bearer <token> estiver presente.

    Usado em fluxos de transição MVP/dev: se não houver token, retorna None.
    Se houver token inválido, bloqueia a requisição com erro genérico.
    """
    if credentials is None:
        return None

    payload = _decode_supabase_token(credentials.credentials)
    return payload["sub"]


def get_user_id(payload: dict = Depends(verify_supabase_token)) -> str:
    """Extrai o user_id do payload do JWT."""
    return payload["sub"]


def get_user_role(payload: dict = Depends(verify_supabase_token)) -> str:
    """Extrai a role do payload do JWT."""
    return payload.get("app_metadata", {}).get("role", "patient")
