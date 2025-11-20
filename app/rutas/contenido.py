from fastapi import APIRouter, HTTPException, Form, File, UploadFile
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import logging

from app.servicios.ia import ServicioIA
from app.repositorios.tokens import GestorTokens
from app.plataformas.tiktok import TikTok as PublicadorTikTok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="")
servicio_ia = ServicioIA()

class SolicitudContenido(BaseModel):
    contenido: str = Field(..., min_length=10)
    redes: List[str]


@router.post("/generar", response_model=Dict[str, Any])
async def generar_contenido(request: SolicitudContenido):

    user_id = "api-user"

    try:
        logger.info(f"Iniciando generación para: {request.redes}")
        
        resultado_ia = servicio_ia.generar_contenido_completo(
            user_id=user_id,
            contenido=request.contenido,
            target_networks=request.redes
        )

        # Ahora "limpiamos" la respuesta para darle el formato exacto que pidió tu frontend
        respuesta_final = {}

        for red in request.redes:
            if red not in resultado_ia:
                continue

            datos_raw = resultado_ia[red]
            
            # Estructura base para la red
            nodo_red = {
                "text": datos_raw.get("text", ""),
                "hashtags": datos_raw.get("hashtags", [])
            }
            
            # Extraer info multimedia y ponerla en 'media_info'
            media_info = {}
            
            if red == "tiktok":
                video_path = datos_raw.get("video_path")
                if video_path:
                    media_info = {
                        "tipo": "video",
                        "archivo_path": video_path,
                    }
            
            elif red == "instagram":
                if "imagen_b64" in datos_raw:
                    media_info = {
                        "tipo": "imagen",
                        "data": "imagen_generada_en_base64"
                    }

            if media_info:
                nodo_red["media_info"] = media_info
            
            respuesta_final[red] = nodo_red
            
        return respuesta_final

    except Exception as e:
        logger.error(f"Error generando contenido: {e}")
        # Es importante ver el error real en la respuesta para debug
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/publicar")
async def tiktok_publicar(
    text: str = Form(...),
    hashtags: str = Form(None),
    archivo: UploadFile = File(...)
):
    current_user_id = "api-user"

    try:
        # 1. Verificar Token
        if not GestorTokens.usuario_tiene_token(current_user_id, "tiktok"):

            publicador = PublicadorTikTok() 
            
            # Generamos link y verifier
            auth_url, verifier = publicador.obtener_url_oauth_con_verifier(current_user_id)
            
            # Guardamos el verifier (CRÍTICO para que funcione el login)
            GestorTokens.guardar_verifier(current_user_id, "tiktok", verifier)
            
            return {
                "estado": "requiere_autenticacion",
                "mensaje": "Debes iniciar sesión en TikTok",
                "auth_url": auth_url
            }

        # 2. Leer video
        video_content = await archivo.read()
        video_size = len(video_content)

        if archivo.content_type != "video/mp4":
            raise HTTPException(status_code=400, detail="Solo MP4")
        
        lista_hashtags = []
        if hashtags:
            # Limpiamos por si el usuario pega "[#tag1, #tag2]" directamente
            limpio = hashtags.replace("[", "").replace("]", "").replace('"', "").replace("'", "")
            # Separamos por comas
            lista_hashtags = [h.strip() for h in limpio.split(",") if h.strip()]

        # 3. Publicar
        publicador = PublicadorTikTok()
        await archivo.seek(0)
        token_data = GestorTokens.obtener_token(current_user_id, "tiktok")
        
        resultado = publicador.publicar_video(
            texto=text,
            video=archivo,
            hashtags=lista_hashtags,
            access_token=token_data["access_token"]
        )

        return {
            "estado": "publicado",
            "success": True,
            "mensaje": "Video enviado a TikTok",
            "resultado": resultado
        }

    except Exception as e:
        logger.error(f"Error publicando en TikTok: {str(e)}")
        return {"estado": "error", "detalle": str(e)}