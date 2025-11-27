import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.rutas.ingreso import router as ingreso_router
from app.rutas.contenido import router as contenido_router
from app.rutas.oauth import router as oauth_router
from app.rutas.historial import router as historial_router

app = FastAPI(title="API Redes Sociales", version="1.0.0")

origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. SERVIR ARCHIVOS ESTÁTICOS (PARA VER LAS FOTOS/VIDEOS)
# Crea la carpeta 'outputs' si no existe
os.makedirs("outputs", exist_ok=True)
os.makedirs("temp", exist_ok=True) # Crear si no existe
app.mount("/temp", StaticFiles(directory="temp"), name="temp")

# Incluir las rutas
app.include_router(ingreso_router)
app.include_router(contenido_router)
app.include_router(oauth_router)
app.include_router(historial_router)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )