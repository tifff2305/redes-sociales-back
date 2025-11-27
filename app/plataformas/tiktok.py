import requests
import os
import base64
import hashlib
import logging
from typing import Dict, Any, Tuple, List
from fastapi import UploadFile

from app.config.configuracion import obtener_configuracion

logger = logging.getLogger(__name__)
config = obtener_configuracion()


def generar_code_verifier(length: int = 64) -> str:
    return base64.urlsafe_b64encode(os.urandom(length)).decode('utf-8').rstrip('=')


def generar_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')


class TikTok:
    
    def __init__(self):
        self.client_key = config.TIKTOK_CLIENT_KEY
        self.client_secret = config.TIKTOK_CLIENT_SECRET
        self.redirect_uri = config.TIKTOK_REDIRECT_URI
        self.auth_url = "https://www.tiktok.com/v2/auth/authorize"
        self.token_url = "https://open.tiktokapis.com/v2/oauth/token/"
        self.api_base = "https://open.tiktokapis.com/v2"
    
    # ==================== OAUTH ====================
    
    def obtener_url_oauth_con_verifier(self, user_id: str) -> Tuple[str, str]:
        verifier = generar_code_verifier()
        challenge = generar_code_challenge(verifier)
        
        # Permisos necesarios
        scopes = "video.upload,video.publish,user.info.basic"
        
        url = f"{self.auth_url}?"
        url += f"client_key={self.client_key}"
        url += f"&scope={scopes}"
        url += f"&response_type=code"
        url += f"&redirect_uri={self.redirect_uri}"
        url += f"&code_challenge={challenge}"
        url += f"&code_challenge_method=S256"
        url += f"&state={user_id}"
        
        logger.info(f"URL OAuth generada para usuario: {user_id}")
        
        return url, verifier
    
    def intercambiar_codigo_por_token(
        self,
        code: str,
        code_verifier: str
    ) -> Dict[str, Any]:

        payload = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier
        }
        
        logger.info("Intercambiando código por token con TikTok")
        
        response = requests.post(self.token_url, data=payload)
        
        # Debug por si falla el token
        if response.status_code != 200:
            logger.error(f"Error TikTok Token: {response.text}")
            
        data = response.json()
        
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
            "open_id": data.get("open_id")
        }
    
    # ==================== PUBLICACIÓN ====================
    
    def publicar_video(
        self,
        texto: str,
        video: Any, 
        access_token: str,
        hashtags: List[str] = None,
        privacy_level: str = "SELF_ONLY"
    ) -> Dict[str, Any]:
 
        # 1. Validar tipo de archivo
        if hasattr(video, 'content_type') and video.content_type != "video/mp4":
            raise ValueError("Solo se permiten archivos MP4")
        
        # 2. LOGICA DE HASHTAGS (Unir texto + hashtags)
        hashtags = hashtags or []
        texto_completo = texto
        
        if hashtags:
            # Formateamos hashtags (#Tag) y los unimos
            hashtags_str = " ".join(
                f"#{h.replace('#', '')}" for h in hashtags
            )
            # Los pegamos al final del texto
            texto_completo = f"{texto}\n\n{hashtags_str}"
        
        # 3. Obtener tamaño del video
        if hasattr(video, 'size'): 
            video_size = video.size
        else:
            video.file.seek(0, 2)
            video_size = video.file.tell()
            video.file.seek(0)
        
        logger.info(f"Publicando en TikTok. Longitud texto: {len(texto_completo)}")
        
        # PASO 1: Inicializar carga
        init_data = self._inicializar_carga(
            description=texto_completo, # Pasamos el texto YA CONCATENADO
            privacy_level=privacy_level,
            video_size=video_size,
            access_token=access_token
        )
        
        upload_url = init_data["upload_url"]
        publish_id = init_data["publish_id"]
        
        # PASO 2: Subir video
        exito = self._subir_video(upload_url, video, video_size)
        
        if not exito:
            raise Exception("Error al subir video a TikTok")
        
        # PASO 3: Completado
        return {
            "success": True,
            "publish_id": publish_id,
            "message": "Video cargado exitosamente. TikTok está procesando.",
            "red_social": "tiktok",
            "texto_publicado": texto_completo
        }
    
    def _inicializar_carga(
        self,
        description: str, 
        privacy_level: str,
        video_size: int,
        access_token: str
    ) -> Dict[str, Any]:
        """Paso 1: Inicializa carga de video"""
        url = f"{self.api_base}/post/publish/video/init/"
        
        # --- CORRECCIÓN AQUÍ: Aumentamos el límite a 2200 caracteres ---
        # Si cortamos a 150, perdemos los hashtags que van al final.
        titulo_completo = description[:2200] 
        
        payload = {
            "post_info": {
                "title": titulo_completo, 
                "privacy_level": privacy_level,
                "description": titulo_completo
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1
            }
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"Error inicializando carga: {error_detail}")
            raise Exception(f"Error inicializando carga en TikTok: {error_detail}")
        
        data = response.json().get("data", {})
        
        if not data.get("upload_url") or not data.get("publish_id"):
            raise Exception("TikTok no proporcionó upload_url o publish_id")
        
        return {
            "upload_url": data["upload_url"],
            "publish_id": data["publish_id"]
        }
    
    def _subir_video(
        self,
        upload_url: str,
        video: Any,
        video_size: int
    ) -> bool:
        """Paso 2: Sube archivo de video"""
        try:
            video.file.seek(0)
            video_content = video.file.read()
            
            headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(video_size),
                "Content-Range": f"bytes 0-{video_size - 1}/{video_size}"
            }
            
            response = requests.put(upload_url, headers=headers, data=video_content)
            
            if response.status_code not in [200, 201]:
                logger.error(f"Error subiendo video: {response.text}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Excepción al subir video: {str(e)}")
            return False
        
# AGREGAR DESPUÉS DE intercambiar_codigo_por_token() en tiktok.py

    def refrescar_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresca un token expirado"""
        payload = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        response = requests.post(self.token_url, data=payload)
        
        if response.status_code != 200:
            raise Exception(f"Error refrescando token: {response.text}")
        
        data = response.json()
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in")
        }