import requests
from typing import Dict, Any
from app.plataformas.base_publicar import PublicadorBase
import os
import base64
import hashlib
import logging 
from fastapi import UploadFile

logger = logging.getLogger(__name__)


def generate_code_verifier(length=64):
    return base64.urlsafe_b64encode(os.urandom(length)).decode('utf-8').rstrip('=')


def generate_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')


class PublicadorTikTok(PublicadorBase):
    
    def __init__(self):
        super().__init__("tiktok")
        self.client_key = os.getenv("TIKTOK_CLIENT_KEY")
        self.client_secret = os.getenv("TIKTOK_CLIENT_SECRET")
        self.auth_url = "https://www.tiktok.com/v2/auth/authorize"
        self.token_url = "https://open.tiktokapis.com/v2/oauth/token/"

    def obtener_url_oauth(self, redirect_uri: str) -> str:
        url, _ = self.obtener_url_oauth_con_verifier(redirect_uri) 
        return url
    
    def obtener_url_oauth_con_verifier(self, redirect_uri: str, user_id: str = None) -> tuple:
        
        verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(verifier)
        
        scopes = "video.upload,video.publish,user.info.basic"
        
        url = f"{self.auth_url}?"
        url += f"client_key={self.client_key}"
        url += f"&scope={scopes}"
        url += f"&response_type=code"
        url += f"&redirect_uri={redirect_uri}"
        url += f"&code_challenge={code_challenge}" 
        url += f"&code_challenge_method=S256"
        
        if user_id:
            url += f"&state={user_id}"
        
        return url, verifier
    
    def intercambiar_codigo_por_token(self, code: str, redirect_uri: str, code_verifier: str = None) -> Dict[str, Any]:
        
        if not code_verifier:
            raise ValueError("code_verifier es requerido para TikTok")
        
        payload = {
            "client_key": self.client_key,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier
        }
        
        response = requests.post(self.token_url, data=payload) 
        
        if response.status_code != 200:
            error_body = response.json() if response.content else response.text
            logger.error(f"❌ TikTok API Error {response.status_code}: {error_body}") 
            raise Exception(f"Error {response.status_code} obteniendo token. Respuesta de TikTok: {error_body}")
        
        data = response.json()
        logger.info(f"✅ TikTok Token Response (200 OK): {data}")
        
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
            "open_id": data.get("open_id")
        }
    
    def publicar(self, contenido: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        
        # Separar texto y hashtags
        texto = contenido.get("text", "")
        hashtags = contenido.get("hashtags", [])

        # Validar texto y hashtags
        if not texto:
            raise ValueError("El texto es obligatorio para publicar en TikTok.")
        if not isinstance(hashtags, list):
            raise ValueError("Los hashtags deben ser una lista.")

        # Limitar el texto a 2200 caracteres
        texto = texto[:2200]

        # Limitar los hashtags a un máximo de 4
        hashtags = hashtags[:4]

        # Definir las variables faltantes
        privacy_level = contenido.get("privacy_level", "SELF_ONLY")
        video_file: UploadFile = contenido.get("video_file")
        video_size: int = contenido.get("video_size")
        init_url = "https://open.tiktokapis.com/v2/post/publish/video/init/"

        # Validar que las variables estén presentes
        if not video_file:
            raise ValueError("TikTok requiere el archivo de video (video_file) para publicar.")
        if not video_size:
            raise ValueError("TikTok requiere el tamaño del video (video_size) para iniciar la carga.")

        # Concatenar hashtags al texto sin incluirlos en la limitación de caracteres
        texto_con_hashtags = texto + " " + " ".join(hashtags)

        # Construir el payload con texto y hashtags concatenados
        init_payload = {
            "post_info": {
                "title": texto[:150] or "Publicación automática",  # Solo el texto para el título
                "privacy_level": privacy_level,
                "description": texto_con_hashtags  # Texto con hashtags concatenados
            },
            "source_info": { 
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1
            }
        }
        
        headers_init = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json" 
        }
        
        logger.info("📤 Paso 1/3: Inicializando carga en TikTok...")
        logger.info(f"Payload: {init_payload}")

        res_init = requests.post(init_url, json=init_payload, headers=headers_init)
        
        logger.info(f"Respuesta de inicialización: {res_init.text}")

        if res_init.status_code != 200:
            logger.error(f"❌ Error init TikTok: {res_init.text}")
            raise Exception(f"Error 1/3 Iniciar carga en TikTok: {res_init.text}")
        
        init_data = res_init.json().get("data", {})
        upload_url = init_data.get("upload_url")
        publish_id = init_data.get("publish_id")
        
        if not upload_url or not publish_id:
            raise Exception("Error 1/3: TikTok no proporcionó upload_url o publish_id.")
            
        logger.info(f"✅ Upload URL obtenida: {upload_url[:80]}...")
        logger.info(f"✅ Publish ID: {publish_id}")
        
        # 2. CARGAR EL ARCHIVO BINARIO - ⚠️ USANDO PUT CON BODY BINARIO
        logger.info("📤 Paso 2/3: Subiendo archivo de video...")
        
        try:
            # Leer el contenido binario del archivo
            video_file.file.seek(0) 
            video_content = video_file.file.read()
            logger.info(f"📦 Archivo leído: {len(video_content)} bytes")
        except Exception as e:
            raise Exception(f"No se pudo leer el archivo de video: {e}")

        # 🚨 CAMBIO CRÍTICO: Usar PUT con Content-Range header
        # TikTok requiere el header Content-Range incluso para un solo chunk
        total_size = len(video_content)
        
        headers_upload = {
            "Content-Type": "video/mp4",
            "Content-Length": str(total_size),
            "Content-Range": f"bytes 0-{total_size - 1}/{total_size}"  # ⚠️ Requerido
        }
        
        logger.info(f"🎬 Subiendo {total_size} bytes a TikTok...")
        logger.info(f"📊 Content-Range: bytes 0-{total_size - 1}/{total_size}")
        
        # PUT request con el contenido binario directamente en el body
        res_upload = requests.put(
            upload_url, 
            headers=headers_upload, 
            data=video_content  # ⚠️ data, no files
        )
        
        logger.info(f"📥 Respuesta de subida: Status {res_upload.status_code}")
        logger.info(f"Cuerpo de respuesta: {res_upload.text[:500]}")
        
        if res_upload.status_code not in [200, 201]:
            logger.error(f"❌ Error upload TikTok: {res_upload.text}")
            raise Exception(f"Error 2/3 Subir archivo a TikTok: {res_upload.text}")
            
        logger.info("✅ Paso 2/3: Video subido exitosamente")
        
        # 3. EL VIDEO ESTÁ SIENDO PROCESADO
        logger.info("✅ Paso 3/3: Publicación completada")
        logger.info(f"🎉 El video está siendo procesado por TikTok con ID: {publish_id}")
        
        return {
            "success": True,
            "publish_id": publish_id,
            "message": "Video cargado exitosamente. Está siendo procesado y publicado por TikTok."
        }