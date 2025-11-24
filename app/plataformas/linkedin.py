import requests
import os
import logging
import base64

logger = logging.getLogger(__name__)

class LinkedinService:
    def __init__(self):
        # URL del webhook de Make.com
        self.webhook_url = os.getenv("ZAPIER_LINKEDIN_WEBHOOK")
        
        if not self.webhook_url:
            raise Exception("❌ Falta ZAPIER_LINKEDIN_WEBHOOK en .env")
        
        logger.info("✅ LinkedIn Service inicializado con Make.com")

    def publicar_post_con_imagen(self, texto: str, ruta_imagen: str):
        """
        Publica en LinkedIn mediante Make.com webhook
        
        Args:
            texto: Contenido del post (incluye hashtags)
            ruta_imagen: Ruta del archivo de imagen en disco
            
        Returns:
            Dict con el resultado de la publicación
        """
        try:
            logger.info("📤 Preparando publicación para LinkedIn via Make.com...")

            # 1. Verificar que la imagen existe
            if not os.path.exists(ruta_imagen):
                raise Exception(f"❌ Imagen no encontrada: {ruta_imagen}")

            # 2. Subir imagen a servicio temporal (imgbb.com - gratis)
            imagen_url = self._subir_imagen_temporal(ruta_imagen)
            
            # 3. Preparar payload para Make.com
            payload = {
                "texto": texto,
                "imagen_url": imagen_url,  # URL pública de la imagen
                "red_social": "linkedin"
            }

            # 4. Enviar a Make.com webhook
            logger.info("🚀 Enviando a Make.com webhook...")
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )

            # 5. Verificar respuesta
            if response.status_code in [200, 201]:
                logger.info("✅ Post enviado exitosamente a LinkedIn via Make.com")
                return {
                    "status": "success",
                    "message": "Publicación enviada a LinkedIn",
                    "webhook_response": response.text
                }
            else:
                logger.error(f"❌ Error de Make.com: {response.status_code} - {response.text}")
                raise Exception(f"Error en Make.com: {response.status_code}")

        except requests.exceptions.Timeout:
            logger.error("❌ Timeout al conectar con Make.com")
            raise Exception("Timeout al publicar en LinkedIn. Intenta de nuevo.")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión con Make.com: {e}")
            raise Exception(f"Error de conexión: {str(e)}")
        
        except Exception as e:
            logger.error(f"❌ Error general en publicación LinkedIn: {e}")
            raise Exception(f"Error publicando en LinkedIn: {str(e)}")
    
    def _subir_imagen_temporal(self, ruta_imagen: str) -> str:
        """
        Sube imagen a ImgBB (servicio gratuito) y retorna URL pública
        
        Args:
            ruta_imagen: Ruta local de la imagen
            
        Returns:
            URL pública de la imagen
        """
        try:
            # API Key gratuita de ImgBB (puedes crear tu propia en imgbb.com/api)
            # Esta es una key pública de ejemplo, crea la tuya
            api_key = os.getenv("IMGBB_API_KEY", "tu_api_key_aqui")
            
            # Leer imagen y convertir a base64
            with open(ruta_imagen, 'rb') as img_file:
                imagen_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            
            # Subir a ImgBB
            response = requests.post(
                "https://api.imgbb.com/1/upload",
                data={
                    "key": api_key,
                    "image": imagen_base64
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                url = data['data']['url']
                logger.info(f"✅ Imagen subida: {url}")
                return url
            else:
                raise Exception(f"Error subiendo imagen: {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Error subiendo imagen temporal: {e}")
            raise Exception(f"No se pudo subir la imagen: {str(e)}")