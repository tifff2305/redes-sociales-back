"""import os
from fastapi import FastAPI, HTTPException, File, UploadFile, Form 
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.core.servicios.NServicio.contenido import ServicioContenido
from app.repositorios.tokens import GestorTokens
from app.plataformas.tiktok import PublicadorTikTok
from app.plataformas.facebook import PublicadorFacebook
from app.api.rutas_oauth import router as oauth_router
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Generador Contenido", version="1.0.0")
app.include_router(oauth_router)

try:
    openai_client = OpenAI()
    servicio_contenido = ServicioContenido(
        openai_client=openai_client,
        modelo_ia="gpt-4o-mini"
    )
    logger.info("✅ Generador inicializado")
except Exception as e:
    logger.error(f"❌ Error inicializando: {e}")
    servicio_contenido = None


class SolicitudContenido(BaseModel):
    contenido: str = Field(..., min_length=10)
    target_networks: List[str]
    user_id: str = "api-user"
    
    class Config:
        json_schema_extra = {
            "example": {
                "contenido": "Lanzamos una característica para gestionar trámites",
                "target_networks": ["tiktok", "facebook"],
                "user_id": "usuario123"
            }
        }
        
@app.post("/generar-contenido", response_model=Dict[str, Any])
async def generar_contenido(request: SolicitudContenido):
    try:
        resultado = servicio_contenido.generar_y_guardar(
            user_id=request.user_id,
            contenido=request.contenido,
            target_networks=request.target_networks
        )
        
        if not resultado:
            raise HTTPException(status_code=500, detail="Error interno: No se generó contenido")
        
        logger.info(f"✅ Contenido generado para {request.user_id}: {', '.join(request.target_networks)}")
        
        response_data = {}
        
        for red in request.target_networks:
            if red in resultado:
                response_data[red] = {
                    "text": resultado[red].get("text"),
                    "hashtags": resultado[red].get("hashtags"),
                    "character_count": resultado[red].get("character_count"),
                }
                
                if red == "tiktok" and "video_hook" in resultado[red]:
                    response_data[red]["video_hook"] = resultado[red]["video_hook"]
                
                if red == "instagram" and "suggested_image_prompt" in resultado[red]:
                    response_data[red]["suggested_image_prompt"] = resultado[red]["suggested_image_prompt"]
        
        # Generar video si la red social es TikTok y se proporciona un video_hook
        if "tiktok" in request.target_networks:
            tiktok_data = resultado.get("tiktok", {})
            video_hook = tiktok_data.get("video_hook")

            if video_hook:
                try:
                    logger.info("🎥 Generando video para TikTok...")
                    servicio_contenido.generar_video(
                        texto=video_hook,
                        duracion=8,  # Duración predeterminada del video
                        ruta_salida=f"outputs/{request.user_id}_tiktok_video.mp4"
                    )
                    logger.info("✔ Video generado exitosamente para TikTok")
                except Exception as e:
                    logger.error(f"❌ Error al generar video para TikTok: {str(e)}")
                    raise HTTPException(status_code=500, detail="Error al generar video para TikTok")
        
        return response_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.post("/publicar", response_model=Dict[str, Any])
async def publicar_contenido(
    user_id: str = Form(...),
    red_social: str = Form(...),
    video_file: UploadFile = File(...),
    texto: Optional[str] = Form(None),
):
    try:
        video_content = await video_file.read()
        video_size = len(video_content)
        video_mime_type = video_file.content_type

        if video_mime_type != "video/mp4":
            raise HTTPException(status_code=400, detail="Solo se permiten archivos de video MP4")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo subido: {str(e)}")

    if not texto:
        try:
            contenido_usuario = servicio_contenido.obtener_de_cache(user_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Debes generar contenido primero usando /generar-contenido con user_id={user_id}"
            )
        
        if red_social not in contenido_usuario:
            redes_disponibles = list(contenido_usuario.keys())
            raise HTTPException(
                status_code=400,
                detail=f"No hay contenido generado para {red_social}. Redes disponibles: {redes_disponibles}"
            )
        
        texto = contenido_usuario[red_social].get("text")
        logger.info(f"✅ Texto recuperado del caché para {user_id}")

    if not GestorTokens.usuario_tiene_token(user_id, red_social):
        raise HTTPException(
            status_code=401,
            detail=f"Usuario no tiene token para {red_social}. Debe conectar su cuenta primero"
        )

    token_data = GestorTokens.obtener_token(user_id, red_social)
    access_token = token_data["access_token"]

    contenido = {
        "text": texto,
        "video_file": video_file,
        "video_size": video_size,
        "privacy_level": "SELF_ONLY"
    }

    try:
        if red_social == "tiktok":
            publicador = PublicadorTikTok()
            resultado = publicador.publicar(contenido, access_token) 

        elif red_social == "facebook":
            page_id = token_data.get("metadata", {}).get("page_id")
            if not page_id:
                raise HTTPException(status_code=400, detail="Facebook requiere page_id")
            publicador = PublicadorFacebook()
            resultado = {"message": "Facebook en desarrollo"}

        else:
            raise HTTPException(status_code=400, detail=f"Red social {red_social} no soportada aún")

        logger.info(f"✅ Publicación exitosa en {red_social.upper()} - ID: {resultado.get('post_id') or resultado.get('publish_id')}")

        return resultado

    except Exception as e:
        logger.error(f"❌ Error publicando en {red_social}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cache/{user_id}")
async def ver_cache_usuario(user_id: str):
    try:
        contenido = servicio_contenido.obtener_de_cache(user_id)
        return {
            "user_id": user_id,
            "redes_disponibles": list(contenido.keys()),
            "contenido": contenido
        }
    except ValueError:
        return {
            "user_id": user_id,
            "contenido": None,
            "mensaje": "No hay contenido en caché para este usuario"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)"""