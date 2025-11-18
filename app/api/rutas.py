from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from openai import OpenAI
from app.core.generador_contenido import GeneradorContenido
from app.db.modelos import GeneracionContenido
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Generador Contenido", version="1.0.0")

try:
    openai_client = OpenAI()
    generador = GeneradorContenido(
        openai_client=openai_client,
        modelo_db=GeneracionContenido,
        modelo_ia="gpt-4o-mini"
    )
    logger.info(" Generador inicializado")
except Exception as e:
    logger.error(f" Error: {e}")
    generador = None


class SolicitudContenido(BaseModel):
    contenido: str = Field(..., min_length=10)
    target_networks: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "contenido": "Lanzamos una característica para gestionar trámites",
                "target_networks": ["facebook", "instagram", "linkedin"]
            }
        }


@app.post("/generar-contenido", response_model=Dict[str, Any])
async def generar_contenido(request: SolicitudContenido):
    
    if not generador:
        raise HTTPException(status_code=500, detail="Servicio no disponible")
    
    redes_validas = ["facebook", "instagram", "linkedin", "tiktok", "whatsapp"]
    redes_invalidas = [red for red in request.target_networks if red not in redes_validas]
    
    if redes_invalidas:
        raise HTTPException(
            status_code=400,
            detail=f"Redes inválidas: {', '.join(redes_invalidas)}"
        )
    
    if not request.target_networks:
        raise HTTPException(status_code=400, detail="target_networks no puede estar vacío")
    
    try:
        resultado = generador.generar_y_guardar_contenido(
            user_id="api-user",
            contenido=request.contenido,
            target_networks=request.target_networks
        )
        
        return resultado
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)