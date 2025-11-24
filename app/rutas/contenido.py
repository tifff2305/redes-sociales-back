from fastapi import APIRouter, HTTPException, Form, File, UploadFile
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import os
import shutil

# Importamos tus servicios
from app.plataformas.whatsapp import WhatsApp
from app.servicios.ia import ServicioIA
from app.repositorios.tokens import GestorTokens
from app.plataformas.tiktok import TikTok
from app.plataformas.facebook import Facebook
from app.plataformas.linkedin import LinkedinService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="")
servicio_ia = ServicioIA()

# Modelo para el endpoint /generar
class SolicitudContenido(BaseModel):
    contenido: str = Field(..., min_length=10)
    redes: List[str]
    telefono_destino: Optional[str] = None


# ==========================================
# 1. ENDPOINT: GENERAR CONTENIDO (IA)
# ==========================================
@router.post("/generar", response_model=Dict[str, Any])
async def generar_contenido(request: SolicitudContenido):
    user_id = "api-user" 

    try:
        logger.info(f"🧠 Iniciando generación IA para: {request.redes}")
        
        # 1. Llamamos al servicio central de IA
        resultado_ia = servicio_ia.generar_contenido_completo(
            user_id=user_id,
            contenido=request.contenido,
            target_networks=request.redes
        )

        respuesta_final = {}

        # 2. Procesamos la respuesta para el Frontend
        for red in request.redes:
            if red not in resultado_ia:
                continue

            datos_raw = resultado_ia[red]
            
            # Estructura base
            nodo_red = {
                "text": datos_raw.get("text", ""),
                "hashtags": datos_raw.get("hashtags", [])
            }
            
            # Información multimedia
            media_info = {}
            
            # --- Caso TikTok (Video) ---
            if red == "tiktok":
                video_path = datos_raw.get("video_path")
                if video_path:
                    media_info = {
                        "tipo": "video",
                        "archivo_path": video_path,
                        "video_hook": datos_raw.get("video_hook")
                    }
            
            # --- Caso Facebook/Instagram (Imagen guardada en outputs) ---
            elif red in ["facebook", "instagram", "linkedin"]:
                media_info = {
                    "tipo": "imagen",
                    # La IA genera una imagen y devuelve la ruta
                    "archivo_path": datos_raw.get("image_path"), 
                    "prompt_usado": datos_raw.get("suggested_image_prompt")
                }

            # --- Caso WhatsApp ---
            elif red == "whatsapp":
                if not request.telefono_destino:
                    respuesta_final[red] = {"error": "Falta teléfono de destino"}
                    continue
                
                cliente_wa = WhatsApp()
                resp = cliente_wa.enviar_contenido_generado(
                    numero_destino=request.telefono_destino,
                    texto_ia=datos_raw["text"]
                )
                nodo_red["estado_envio"] = f"Enviado (ID: {resp.get('messages', [{}])[0].get('id')})"

            if media_info:
                nodo_red["media_info"] = media_info
            
            respuesta_final[red] = nodo_red
            
        return respuesta_final

    except Exception as e:
        logger.error(f"❌ Error generando contenido: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno IA: {str(e)}")


# ==========================================
# 2. ENDPOINT: PUBLICAR (Redes Sociales)
# ==========================================
@router.post("/publicar")
async def publicar_contenido(
    red_social: str = Form(..., description="tiktok, facebook, instagram, linkedin"),
    text: str = Form(...),
    hashtags: str = Form(None),
    archivo: UploadFile = File(...), 
):
    current_user_id = "api-user"

    try:
        logger.info(f"🚀 Solicitud de publicación para: {red_social}")

        # Procesar hashtags 
        texto_final = text
        lista_hashtags = []
        if hashtags:
            limpio = hashtags.replace("[", "").replace("]", "").replace('"', "").replace("'", "")
            lista_hashtags = [h.strip() for h in limpio.split(",") if h.strip()]
            tags_str = " ".join(f"#{t}" if not t.startswith("#") else t for t in lista_hashtags)
            texto_final = f"{text}\n\n{tags_str}"

        # ================= TIKTOK =================
        if red_social == "tiktok":
            if not GestorTokens.usuario_tiene_token(current_user_id, "tiktok"):
                raise HTTPException(status_code=400, detail="Falta autenticación TikTok.")
            return await _manejar_publicacion_tiktok(current_user_id, text, lista_hashtags, archivo)

        # ================= FACEBOOK =================
        elif red_social == "facebook":
            contenido_imagen = await archivo.read()
            fb_service = Facebook()
            post_id = fb_service.publicar_foto(archivo_binario=contenido_imagen, mensaje=texto_final)
            return {"estado": "publicado", "success": True, "post_id": post_id, "red": "facebook"}

        # ================= LINKEDIN (NUEVO) =================
        elif red_social == "linkedin":
            # 1. Guardar archivo temporalmente (la librería necesita una ruta de disco)
            temp_filename = f"temp_{archivo.filename}"
            
            try:
                # Escribimos el archivo subido al disco
                with open(temp_filename, "wb") as buffer:
                    shutil.copyfileobj(archivo.file, buffer)
                
                # 2. Instanciar servicio y publicar
                lnk_service = LinkedinService()
                resultado = lnk_service.publicar_post_con_imagen(
                    texto=texto_final,
                    ruta_imagen=temp_filename
                )
                
                return {
                    "estado": "publicado",
                    "success": True,
                    "red": "linkedin",
                    "api_response": str(resultado) # LinkedIn a veces devuelve vacio si es 201 Created
                }

            except Exception as e:
                logger.error(f"Error LinkedIn: {e}")
                raise HTTPException(status_code=500, detail=f"Fallo LinkedIn: {str(e)}")
            
            finally:
                # 3. Limpieza: Borrar archivo temporal siempre (aunque falle)
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

        else:
            raise HTTPException(status_code=400, detail=f"Red social '{red_social}' no soportada aún")

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error crítico publicando: {str(e)}")
        return {"estado": "error", "detalle": str(e)}


# ==========================================
# 3. MÉTODOS PRIVADOS (Helpers)
# ==========================================

async def _manejar_publicacion_tiktok(user_id, text, hashtags, archivo):
    """Maneja la lógica de TikTok incluyendo el reintento por token vencido"""
    tiktok_service = TikTok()
    
    # 1. Obtener token
    token_data = GestorTokens.obtener_token(user_id, "tiktok")
    if not token_data:
         raise HTTPException(status_code=400, detail="Error de tokens TikTok")
         
    access_token = token_data["access_token"]
    
    try:
        # 2. Intentar publicar
        await archivo.seek(0) # Asegurar inicio del archivo
        resultado = tiktok_service.publicar_video(
            texto=text,
            video=archivo,
            hashtags=hashtags,
            access_token=access_token
        )
        return resultado

    except Exception as e:
        # 3. Capturar error de token vencido
        error_str = str(e).lower()
        if "401" in error_str or "access token expired" in error_str or "invalid_grant" in error_str:
            
            logger.warning("⚠️ Token TikTok vencido. Intentando auto-refresh...")
            
            refresh_token = token_data.get("refresh_token")
            if not refresh_token:
                raise HTTPException(status_code=401, detail="Token vencido. Reconecta tu cuenta.")

            try:
                # A. Refrescar Token
                nuevo_token = tiktok_service.refrescar_token(refresh_token)
                
                # B. Guardar nuevo token
                GestorTokens.guardar_token(
                    user_id=user_id,
                    red_social="tiktok",
                    access_token=nuevo_token["access_token"],
                    refresh_token=nuevo_token.get("refresh_token", refresh_token),
                    expires_in=nuevo_token.get("expires_in")
                )
                
                # C. Reintentar Publicación
                logger.info("🔄 Reintentando publicación con nuevo token...")
                await archivo.seek(0)
                resultado = tiktok_service.publicar_video(
                    texto=text,
                    video=archivo,
                    hashtags=hashtags,
                    access_token=nuevo_token["access_token"]
                )
                return resultado

            except Exception:
                raise HTTPException(status_code=401, detail="Tu sesión expiró completamente. Por favor conecta TikTok nuevamente.")
        
        else:
            raise e