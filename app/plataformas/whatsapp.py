import requests
import os
import base64
import logging
import mimetypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhatsApp:
    def __init__(self):
        self.token = os.getenv("WHAPI_TOKEN")
        self.base_url = os.getenv("WHAPI_URL", "https://gate.whapi.cloud/")
        # Si tienes un número de prueba o tu propio número, ponlo aquí o en el .env
        self.contact_id = os.getenv("WHAPI_CONTACT_ID", "59176316283") # Usé el del ejemplo
        
        if not self.token:
            logger.error("❌ No se encontró WHAPI_TOKEN")

    def publicar_foto(self, archivo_binario: bytes, mensaje: str, nombre_archivo: str):
        """
        Publica historia replicando EXACTAMENTE el script funcional.
        """
        if not self.token:
            raise Exception("Falta WHAPI_TOKEN")

        base = self.base_url.strip().rstrip("/")
        url_endpoint = f"{base}/stories/send/media"

        # 1. Detectar Mime Type (Tu script usaba png, aquí detectamos el real)
        mime_type, _ = mimetypes.guess_type(nombre_archivo)
        if not mime_type:
            mime_type = "image/jpeg"

        try:
            # 2. Codificar Base64
            b64_string = base64.b64encode(archivo_binario).decode("utf-8")
            
            # 3. Construir cadena Data URI con 'name=' (Vital para Whapi)
            media_data = f"data:{mime_type};name={nombre_archivo};base64,{b64_string}"
            
        except Exception as e:
            raise Exception(f"Error codificando Base64: {e}")

        # 4. Payload IDÉNTICO a tu script funcional
        # La clave aquí es el campo 'contacts'. Sin él, da error 400.
        payload = {
            "media": media_data,
            "caption": mensaje,
            "contacts": [self.contact_id] if self.contact_id else [] 
        }
        
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.token}",
            "content-type": "application/json"
        }

        logger.info(f"🚀 Enviando a: {url_endpoint}")
        logger.info(f"📋 Params: {mime_type} | Contactos: {payload['contacts']}")
        
        try:
            response = requests.post(url_endpoint, headers=headers, json=payload, timeout=45)
            
            if response.status_code >= 400:
                logger.error(f"❌ Error Whapi ({response.status_code}): {response.text}")
                
            response.raise_for_status()
            
            result = response.json()
            # Whapi devuelve a veces el ID o el estado 'sent'
            msg_id = result.get('id', result.get('sent', 'Enviado'))
            
            logger.info(f"✅ Historia publicada: {msg_id}")
            return str(msg_id)
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error Whapi: {e}")