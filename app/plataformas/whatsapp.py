import requests
import os
import base64
import logging

logger = logging.getLogger(__name__)

class WhatsApp:
    def __init__(self):
        self.token = os.getenv("WHAPI_TOKEN")
        self.base_url = "https://gate.whapi.cloud"
        
        if not self.token:
            logger.error("❌ No se encontró WHAPI_TOKEN en variables de entorno")

    def _convertir_a_base64(self, ruta_archivo):
        """Convierte imagen/video a Base64 para Whapi"""
        with open(ruta_archivo, "rb") as file:
            encoded_string = base64.b64encode(file.read()).decode('utf-8')
        
        ext = ruta_archivo.split('.')[-1].lower()
        # Determinar MIME type correcto
        if ext in ["mp4", "mov", "avi"]:
            mime = "video/mp4"
        elif ext in ["png"]:
            mime = "image/png"
        else:
            mime = "image/jpeg"
            
        return f"data:{mime};name=estado.{ext};base64,{encoded_string}"

    def publicar_estado(self, ruta_archivo, texto):
        """
        Publica contenido en el Estado (Status).
        Target fijo: 'status@broadcast'
        """
        if not self.token:
            raise Exception("Falta WHAPI_TOKEN")

        # 1. Preparar archivo
        media_b64 = self._convertir_a_base64(ruta_archivo)
        
        # 2. Elegir endpoint según extensión
        ext = ruta_archivo.split('.')[-1].lower()
        es_video = ext in ["mp4", "mov", "avi"]
        endpoint = "/messages/video" if es_video else "/messages/image"
        
        # 3. Configurar payload
        payload = {
            "to": "status@broadcast",  # <--- MAGIA: Esto lo manda a tu Estado
            "media": media_b64,
            "caption": texto
        }
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        logger.info(f"📱 Subiendo Estado a WhatsApp ({endpoint})...")
        
        try:
            response = requests.post(f"{self.base_url}{endpoint}", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error Whapi: {e}")
            if e.response is not None:
                logger.error(f"Detalle API: {e.response.text}")
            raise Exception(f"Error publicando estado: {e}")