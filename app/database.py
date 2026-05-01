"""
database.py — Conexão única com Supabase (padrão Singleton)

Garante que existe apenas uma instância do cliente Supabase
em toda a aplicação. Isso é importante para:
- Performance (reutiliza conexão)
- Consistência (não há múltiplas instâncias conflitantes)
- Facilidade de teste (pode ser mockado em um lugar)
"""

import os
from supabase import create_client, Client
from functools import lru_cache
from dotenv import load_dotenv

# Garante que .env seja carregado antes de qualquer os.getenv()
load_dotenv()

@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Cria e retorna uma instância única do cliente Supabase.
    
    Por que SERVICE_KEY no backend?
    - SERVICE_KEY bypassa RLS (Row Level Security).
    - O FastAPI aplica verificação de permissão manualmente no código.
    - Isso dá controle total ao backend sobre quem acessa o quê.
    
    Por que não usar anon key?
    - Anon key respeita RLS automaticamente.
    - Isso é bom para o app (Flutter), mas no backend você quer
      flexibilidade para queries administrativas.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_KEY são obrigatórios")
    
    return create_client(url, key)

# Instância global — importada pelos routes
supabase: Client = get_supabase_client()
