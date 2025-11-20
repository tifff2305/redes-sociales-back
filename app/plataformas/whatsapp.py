import requests
import logging
import json
from typing import Dict, Any

from app.config.configuracion import obtener_configuracion

logger = logging.getLogger(__name__)

class WhatsApp:
    
    def __init__(self):
        config = obtener_configuracion()
        self.token = config.WHATSAPP_TOKEN
        self.phone_id = config.WHATSAPP_PHONE_ID
        self.version = config.WHATSAPP_VERSION
        self.base_url = f"https://graph.facebook.com/{self.version}"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def enviar_contenido_generado(self, numero_destino: str, texto_ia: str) -> Dict[str, Any]:

        texto_seguro = texto_ia[:1000] 

        url = f"{self.base_url}/{self.phone_id}/messages"
        
        # Estructura exacta para enviar variables (parameters)
        payload = {
            "messaging_product": "whatsapp",
            "to": numero_destino,
            "type": "template",
            "template": {
                "name": "contenido_generado",  # <--- TU PLANTILLA
                "language": {
                    "code": "es"  # "es" es el código estándar para Español genérico
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": texto_seguro  # <--- Aquí va lo que generó la IA
                            }
                        ]
                    }
                ]
            }
        }

        try:
            logger.info(f"📱 Enviando WhatsApp a {numero_destino}...")
            response = requests.post(url, headers=self.headers, data=json.dumps(payload))
            
            # Si falla (ej: 400 o 401), lanzamos error para verlo en el log
            response.raise_for_status()
            
            data = response.json()
            logger.info(f" Mensaje enviado con éxito. ID: {data.get('messages', [{}])[0].get('id')}")
            return data

        except requests.exceptions.RequestException as e:
            error_msg = f"Error enviando WhatsApp: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                # Esto imprime el error exacto que devuelve Meta (muy útil para depurar)
                logger.error(f" Detalle Error Meta: {e.response.text}")
            else:
                logger.error(f" {error_msg}")
            raise ValueError(error_msg)