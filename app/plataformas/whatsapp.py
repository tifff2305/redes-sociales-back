import requests
import os
import base64
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsApp:
    def __init__(self):
        self.token = os.getenv("WHAPI_TOKEN")
        self.base_url = os.getenv("WHAPI_URL", "https://gate.whapi.cloud")
        
        if not self.token:
            logger.error("❌ No se encontró WHAPI_TOKEN")

    def publicar_estado(self, archivo_binario: bytes, nombre_archivo: str, caption: str):
        """
        EXACTO según tu imagen:
        - Endpoint: /stories/send/media
        - Payload: SOLO media y caption (SIN contacts)
        """
        if not self.token:
            raise Exception("Falta WHAPI_TOKEN")

        # Endpoint EXACTO de tu imagen
        base = self.base_url.rstrip("/")
        url = f"{base}/stories/send/media"

        # Construir Base64 EXACTO como tu imagen
        try:
            b64_bytes = base64.b64encode(archivo_binario)
            b64_string = b64_bytes.decode('utf-8')
            
            # Detectar MIME type
            ext = nombre_archivo.split('.')[-1].lower()
            mime = "image/jpeg"
            if ext == "png":
                mime = "image/png"
            elif ext in ["mp4", "mov"]:
                mime = "video/mp4"

            # Formato EXACTO: data:image/png;name=archivo.png;base64,datos
            media_data = f"data:{mime};name={nombre_archivo};base64,{b64_string}"
            
        except Exception as e:
            raise Exception(f"Error Base64: {e}")

        # Payload EXACTO como tu imagen (SIN contacts)
        payload = {
            "media": media_data, 
            "caption": caption
        }
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        logger.info(f"🚀 Enviando story a: {url}")
        logger.info(f"📦 Payload estructura: media + caption (sin contacts)")
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code >= 400:
                logger.error(f"❌ Error API ({response.status_code}): {response.text}")
                
            response.raise_for_status()
            logger.info("✅ Historia publicada exitosamente")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error Whapi: {e}")