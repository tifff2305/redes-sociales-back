from fastapi import APIRouter, HTTPException, Form, File, UploadFile
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import os
import shutil
import uuid

# Importamos tus servicios
from app.plataformas.instagram import Instagram
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
            elif red in ["facebook", "instagram", "linkedin", "whatsapp"]:
                image_path = datos_raw.get("image_path")
                
                if image_path:
                    media_info = {
                        "tipo": "imagen",
                        "archivo_path": image_path
                    }
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
    # Aceptamos una cadena separada por comas: "tiktok,facebook,linkedin"
    red_social: str = Form(..., description="Lista separada por comas ej: 'tiktok,facebook'"),
    text: str = Form(...),
    hashtags: str = Form(None),
    archivo: UploadFile = File(...), 
):
    current_user_id = "api-user"
    
    # 1. Separar la lista de redes
    # Si llega "tiktok, facebook", crea ["tiktok", "facebook"]
    lista_redes = [r.strip().lower() for r in red_social.split(",") if r.strip()]
    
    logger.info(f"🚀 Iniciando publicación masiva para: {lista_redes}")

    # 2. Preparar Texto
    lista_hashtags = []
    texto_final = text
    if hashtags:
        limpio = hashtags.replace("[", "").replace("]", "").replace('"', "").replace("'", "")
        lista_hashtags = [h.strip() for h in limpio.split(",") if h.strip()]
        tags_str = " ".join(f"#{t}" if not t.startswith("#") else t for t in lista_hashtags)
        texto_final = f"{text}\n\n{tags_str}"

    # 3. Guardar archivo temporalmente en disco (CRÍTICO para reusarlo)
    # Lo guardamos una vez y todas las redes leen de ahí.
    os.makedirs("temp", exist_ok=True)
    ext = archivo.filename.split(".")[-1]
    nombre_temp = f"temp_{uuid.uuid4()}.{ext}"
    ruta_temp = os.path.join("temp", nombre_temp)
    
    try:
        with open(ruta_temp, "wb") as buffer:
            shutil.copyfileobj(archivo.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando archivo temporal: {e}")

    # 4. Bucle de Publicación
    resultados = {} # Aquí guardaremos qué pasó con cada red

    try:
        for red in lista_redes:
            try:
                logger.info(f"📤 Enviando a {red}...")
                
                # --- TIKTOK ---
                if red == "tiktok":
                    if not GestorTokens.usuario_tiene_token(current_user_id, "tiktok"):
                        resultados[red] = {"status": "error", "detalle": "Falta conectar cuenta (Token)"}
                        continue
                    
                    if "mp4" not in ext.lower():
                        resultados[red] = {"status": "error", "detalle": "TikTok requiere video .mp4"}
                        continue

                    tk_service = TikTok()
                    token_data = GestorTokens.obtener_token(current_user_id, "tiktok")
                    
                    # TikTokService suele esperar un archivo abierto ('rb')
                    with open(ruta_temp, "rb") as video_file:
                         res = tk_service.publicar_video(
                            texto=text, # TikTok prefiere texto limpio sin tags pegados
                            video=video_file,
                            hashtags=lista_hashtags,
                            access_token=token_data["access_token"]
                        )
                    resultados[red] = {"status": "ok", "api_response": res}

                # --- FACEBOOK ---
                elif red == "facebook":
                    fb_service = Facebook()
                    # Leemos bytes del disco
                    with open(ruta_temp, "rb") as img_file:
                        bytes_img = img_file.read()
                        res = fb_service.publicar_foto(archivo_binario=bytes_img, mensaje=texto_final)
                    resultados[red] = {"status": "ok", "post_id": res}

                # --- INSTAGRAM ---
                elif red == "instagram":
                    ig_service = Instagram()
                    with open(ruta_temp, "rb") as img_file:
                        bytes_img = img_file.read()
                        res = ig_service.publicar_foto(archivo_binario=bytes_img, mensaje=texto_final)
                    resultados[red] = {"status": "ok", "post_id": res}

                # --- LINKEDIN ---
                elif red == "linkedin":
                    lnk_service = LinkedinService()
                    # LinkedIn necesita la RUTA del archivo, no los bytes. ¡Perfecto, ya la tenemos!
                    res = lnk_service.publicar_post_con_imagen(texto=texto_final, ruta_imagen=ruta_temp)
                    resultados[red] = {"status": "ok", "api_response": str(res)}

                # --- WHATSAPP ---
                elif red == "whatsapp":
                    wa_service = WhatsApp()
                    # Aquí llamamos al nuevo método exclusivo para estados
                    res = wa_service.publicar_estado(
                        ruta_archivo=ruta_temp,
                        texto=texto_final # Incluye los hashtags si los hay
                    )
                    # Whapi devuelve algo como: {'messages': [{'id': 'ABEG...', ...}]}
                    msg_id = res.get('messages', [{}])[0].get('id', 'Enviado')
                    resultados[red] = {"status": "ok", "post_id": msg_id}

                else:
                    resultados[red] = {"status": "error", "detalle": "Red no soportada"}

            except Exception as e_red:
                logger.error(f"❌ Falló {red}: {e_red}")
                resultados[red] = {"status": "error", "detalle": str(e_red)}

        return {
            "resumen": "Proceso finalizado",
            "detalles": resultados
        }

    finally:
        # Limpieza
        if os.path.exists(ruta_temp):
            try:
                os.remove(ruta_temp)
            except:
                pass


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