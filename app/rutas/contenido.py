from fastapi import APIRouter, HTTPException, Form, File, UploadFile, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging
import os
import shutil
import uuid
import json

# --- IMPORTACIONES DE TUS MÓDULOS ---
from app.config.bd import obtener_bd
from app.modelos.esquemas import SolicitudGenerarContenido
from app.modelos.tablas import Usuario, Chat, Mensaje
from app.utilidades.dependencia import obtener_usuario_actual
from app.servicios.ia import ServicioIA

# --- SERVICIOS ---
from app.servicios.aws_s3 import GestorS3  # <--- NUEVO: Para subir a la nube
from app.plataformas.instagram import Instagram
from app.plataformas.whatsapp import WhatsApp
from app.plataformas.tiktok import TikTok
from app.plataformas.facebook import Facebook
from app.plataformas.linkedin import LinkedinService
from app.repositorios.tokens import GestorTokens

logger = logging.getLogger(__name__)

router = APIRouter(prefix="")
servicio_ia = ServicioIA()

# ==========================================
# 1. ENDPOINT: GENERAR CONTENIDO
# ==========================================
@router.post("/generar", response_model=Dict[str, Any])
async def generar_contenido(
    request: SolicitudGenerarContenido,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_bd)
):
    try:
        logger.info(f"🧠 Usuario {usuario_actual.id} generando contenido...")

        # 1. Crear Chat en BD
        nuevo_chat = Chat(
            usuario_id=usuario_actual.id,
            titulo=f"{request.contenido[:20]}..."
        )
        db.add(nuevo_chat)
        db.commit()
        db.refresh(nuevo_chat)
        
        # 2. Guardar Prompt
        mensaje_user = Mensaje(
            chat_id=nuevo_chat.id,
            rol="user",
            contenido=request.contenido,
            redes_objetivo=",".join(request.target_networks)
        )
        db.add(mensaje_user)
        db.commit()

        # 3. Llamar a la IA
        resultado_ia = servicio_ia.generar_contenido_completo(
            user_id=str(usuario_actual.id),
            contenido=request.contenido,
            target_networks=request.target_networks
        )

        # 4. Procesar respuesta
        respuesta_final = {}
        for red in request.target_networks:
            if red not in resultado_ia: continue

            datos_raw = resultado_ia[red]
            nodo_red = {
                "text": datos_raw.get("text", ""),
                "hashtags": datos_raw.get("hashtags", [])
            }
            
            media_info = {}
            if red == "tiktok":
                video_path = datos_raw.get("video_path")
                if video_path:
                    media_info = {"tipo": "video", "archivo_path": video_path, "video_hook": datos_raw.get("video_hook")}
            elif red in ["facebook", "instagram", "linkedin", "whatsapp"]:
                image_path = datos_raw.get("image_path")
                if image_path:
                    media_info = {"tipo": "imagen", "archivo_path": image_path}

            if media_info:
                nodo_red["media_info"] = media_info
            
            respuesta_final[red] = nodo_red

        # 5. Guardar respuesta en BD
        mensaje_assistant = Mensaje(
            chat_id=nuevo_chat.id,
            rol="assistant",
            # CAMBIO AQUÍ: Usar json.dumps para que se guarde con comillas dobles ""
            contenido=json.dumps(respuesta_final), 
            redes_objetivo=",".join(request.target_networks)
        )
        db.add(mensaje_assistant)
        db.commit()

        return respuesta_final

    except Exception as e:
        logger.error(f"❌ Error generando contenido: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno IA: {str(e)}")


# ==========================================
# 2. ENDPOINT: PUBLICAR (CON AWS S3)
# ==========================================
@router.post("/publicar")
async def publicar_contenido(
    red_social: str = Form(...),
    text: str = Form(...),
    hashtags: str = Form(None),
    archivo: UploadFile = File(...),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_bd)
):
    current_user_id = str(usuario_actual.id)
    lista_redes = [r.strip().lower() for r in red_social.split(",") if r.strip()]
    logger.info(f"🚀 Usuario {usuario_actual.email} publicando en: {lista_redes}")

    # 1. Guardar archivo temporalmente en disco
    os.makedirs("temp", exist_ok=True)
    ext = archivo.filename.split(".")[-1]
    nombre_temp = f"temp_{uuid.uuid4()}.{ext}"
    ruta_temp = os.path.join("temp", nombre_temp)
    
    try:
        with open(ruta_temp, "wb") as buffer:
            shutil.copyfileobj(archivo.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando archivo temporal: {e}")

    # 2. Preparar Texto
    texto_final = text
    if hashtags:
        limpio = hashtags.replace("[", "").replace("]", "").replace('"', "").replace("'", "")
        lista_hashtags = [h.strip() for h in limpio.split(",") if h.strip()]
        tags_str = " ".join(f"#{t}" if not t.startswith("#") else t for t in lista_hashtags)
        texto_final = f"{text}\n\n{tags_str}"
    else:
        lista_hashtags = []

    # 3. SUBIR A AWS S3 (Si es necesario)
    """url_publica_s3 = ""
    redes_que_piden_url = ["instagram", "whatsapp"] # Redes que prefieren URL
    necesita_subida = any(r in lista_redes for r in redes_que_piden_url)

    if necesita_subida:
        try:
            logger.info("☁️ Subiendo archivo a AWS S3...")
            s3_service = GestorS3()
            # Subimos el archivo y obtenemos la URL pública (https://bucket...)
            url_publica_s3 = s3_service.subir_archivo(ruta_temp, nombre_temp)
        except Exception as e:
            logger.error(f"Error S3: {e}")
            # No detenemos el proceso, quizás otras redes (TikTok) funcionen localmente
            url_publica_s3 = None """

    resultados = {}

    try:
        for red in lista_redes:
            try:
                # --- TIKTOK (Usa archivo local) ---
                if red == "tiktok":
                    # Verificar token en BD
                    if not GestorTokens.usuario_tiene_token(db, int(current_user_id), "tiktok"):
                        resultados[red] = {"status": "error", "detalle": "Falta conectar cuenta (Token)"}
                        continue
                    
                    # Usamos helper para manejar refresh token
                    with open(ruta_temp, "rb") as video_file:
                        res = await _manejar_publicacion_tiktok(
                            db, # Pasamos BD
                            int(current_user_id), 
                            texto_final, 
                            lista_hashtags, 
                            video_file
                        )
                    resultados[red] = {"status": "ok", "api_response": res}

                # --- WHATSAPP (Usa URL de S3) ---
                elif red == "whatsapp":
                    wa_service = WhatsApp()
                    
                    with open(ruta_temp, "rb") as img_file:
                        # LE PASAMOS EL NOMBRE REAL DEL ARCHIVO
                        # Esto es lo que rellena la parte "name={nombre_imagen}"
                        res = wa_service.publicar_foto(
                            archivo_binario=img_file.read(), 
                            mensaje=texto_final,
                            nombre_archivo=archivo.filename 
                        )

                    resultados[red] = {"status": "ok", "post_id": res}

                # --- INSTAGRAM (Usa URL de S3) ---
                elif red == "instagram":
                    ig_service = Instagram()
                    # Leer el archivo a bytes
                    with open(ruta_temp, "rb") as img_file:
                        res = ig_service.publicar_foto(
                            archivo_binario=img_file.read(), 
                            mensaje=texto_final
                        )

                    resultados[red] = {"status": "ok", "post_id": res}

                # --- FACEBOOK (Usa Bytes) ---
                elif red == "facebook":
                     fb_service = Facebook()
                     with open(ruta_temp, "rb") as img_file:
                        res = fb_service.publicar_foto(img_file.read(), texto_final)
                     resultados[red] = {"status": "ok", "post_id": res}

                # --- LINKEDIN (Usa ruta local o bytes) ---
                elif red == "linkedin":
                     lnk_service = LinkedinService()
                     res = lnk_service.publicar_post_con_imagen(texto_final, ruta_temp)
                     resultados[red] = {"status": "ok", "api_response": str(res)}

            except Exception as e_red:
                logger.error(f"❌ Falló {red}: {e_red}")
                resultados[red] = {"status": "error", "detalle": str(e_red)}

        return {"resumen": "Proceso finalizado", "detalles": resultados}

    finally:
        if os.path.exists(ruta_temp):
            try:
                os.remove(ruta_temp)
            except:
                pass

# ==========================================
# 3. HELPERS
# ==========================================
async def _manejar_publicacion_tiktok(db: Session, user_id: int, text, hashtags, archivo_obj):
    """Maneja TikTok con reintento de token"""
    tiktok_service = TikTok()
    
    token_data = GestorTokens.obtener_token(db, user_id, "tiktok")
    if not token_data:
         raise Exception("Error recuperando token TikTok de BD")
         
    access_token = token_data["access_token"]
    
    try:
        # Intentar publicar
        return tiktok_service.publicar_video(text, archivo_obj, hashtags, access_token)

    except Exception as e:
        error_str = str(e).lower()
        if "401" in error_str or "access token expired" in error_str:
            logger.warning("⚠️ Token TikTok vencido. Refrescando...")
            
            refresh_token = token_data.get("refresh_token")
            if not refresh_token:
                raise Exception("Token vencido y sin refresh token.")

            # Refrescar
            nuevo = tiktok_service.refrescar_token(refresh_token)
            
            # Guardar nuevo
            GestorTokens.guardar_token(
                db, user_id, "tiktok",
                nuevo["access_token"],
                nuevo.get("refresh_token", refresh_token),
                nuevo.get("expires_in")
            )
            
            # Reintentar
            archivo_obj.seek(0)
            return tiktok_service.publicar_video(text, archivo_obj, hashtags, nuevo["access_token"])
        else:
            raise e