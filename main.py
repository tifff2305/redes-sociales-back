# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat_routes import router as chat_router

# Crear la aplicación
app = FastAPI(
    title="Redis Sociales API",
    description="API para generar contenido de redes sociales con IA",
    version="1.0.0"
)

# Permitir peticiones desde el frontend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar las rutas del chat
app.include_router(chat_router)

# Ruta raíz
@app.get("/")
def inicio():
    return {
        "mensaje": "API de Redis Sociales",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Health check
@app.get("/health")
def verificar_salud():
    return {"status": "ok"}

# Para ejecutar directamente
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)