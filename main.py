"""
main.py — Aplicação FastAPI principal para AURA
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import logs
from app.config import DEBUG, APP_NAME, APP_VERSION

app = FastAPI(
    title=APP_NAME,
    description="API de acompanhamento psiquiátrico",
    version=APP_VERSION
)

# CORS: permite requisições do app Flutter
# Em produção, especifique os domínios exatos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if DEBUG else ["https://seu-dominio.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rotas
app.include_router(logs.router)

@app.get("/health")
async def health_check():
    """Endpoint de health check."""
    return {"status": "ok", "version": APP_VERSION}

@app.get("/")
async def root():
    """Endpoint raiz."""
    return {
        "message": "Bem-vindo à AURA API",
        "version": APP_VERSION,
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG
    )
