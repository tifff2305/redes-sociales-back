import uvicorn
from app.api.rutas import app

if __name__ == "__main__":
    uvicorn.run(
        "app.api.rutas:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )