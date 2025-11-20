from fastapi import FastAPI
from app.rutas.contenido import router as contenido_router
from app.rutas.oauth import router as oauth_router

app = FastAPI(title="API Redes Sociales", version="1.0.0")

# Incluir las rutas
app.include_router(contenido_router)
app.include_router(oauth_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )