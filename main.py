"""
main.py - Aplicacao FastAPI principal para AURA
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import consent, dashboard, devices, logs, modules, patients
from app.config import APP_NAME, APP_VERSION, DEBUG
from app.database import supabase

app = FastAPI(
    title=APP_NAME,
    description="API de acompanhamento psiquiatrico",
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if DEBUG else ["https://seu-dominio.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs.router)
app.include_router(patients.router)
app.include_router(modules.router)
app.include_router(consent.router)
app.include_router(dashboard.router)
app.include_router(devices.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/db-check")
async def db_check():
    try:
        supabase.table("patients").select("id").limit(1).execute()
        return {"status": "ok", "database": "connected"}
    except Exception:
        return {
            "status": "error",
            "database": "unavailable",
            "detail": "Supabase query failed",
        }


@app.get("/")
async def root():
    return {
        "message": "Bem-vindo a AURA API",
        "version": APP_VERSION,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
    )
