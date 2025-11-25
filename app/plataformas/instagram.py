import requests
import logging
import time
from typing import List, Dict, Any

# Ajusta estos imports según tu estructura de carpetas
from app.config.configuracion import obtener_configuracion

logger = logging.getLogger(__name__)

class Instagram:
    
    def __init__(self):
        config = obtener_configuracion()
        self.ig_user_id = config.INSTAGRAM_APP_ID
        self.access_token = config.INSTAGRAM_PAGE_ACCESS_TOKEN
        self.imgbb_key = config.IMGBB_API_KEY             
        
        self.base_url = "https://graph.facebook.com/v18.0"

        if not self.ig_user_id:
            logger.warning("⚠️ Falta INSTAGRAM_BUSINESS_ACCOUNT_ID en la configuración")

    # ==================== PUBLICACIÓN CON IMGBB ====================
    def publicar_foto(self, archivo_binario, mensaje: str) -> str:
        """
        Recibe bytes de imagen, los sube a ImgBB para obtener URL y publica en IG.
        """
        logger.info("🚀 Iniciando publicación en Instagram...")

        try:
            # PASO 0: Convertir bytes a URL pública usando ImgBB
            image_url = self._subir_a_hosting_temporal(archivo_binario)
            
            # PASO 1: Crear contenedor de medios en Instagram
            creation_id = self._crear_contenedor(image_url, mensaje)
            
            # PASO 2: Publicar el contenedor
            post_id = self._publicar_contenedor(creation_id)
            
            return post_id

        except Exception as e:
            logger.error(f"❌ Error en publicación Instagram: {e}")
            raise e

    # ==================== MÉTODOS PRIVADOS ====================

    def _subir_a_hosting_temporal(self, image_bytes) -> str:
        """Sube la imagen a ImgBB para obtener una URL pública temporal"""
        logger.info("🌐 Subiendo imagen a servidor temporal (ImgBB)...")
        url_imgbb = "https://api.imgbb.com/1/upload"
        
        payload = {
            "key": self.imgbb_key,
            "expiration": 600  # La imagen se borra sola en 10 minutos (seguridad)
        }
        files = {
            "image": image_bytes
        }
        
        try:
            resp = requests.post(url_imgbb, data=payload, files=files, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            public_url = data["data"]["url"]
            logger.info(f"✅ URL temporal generada: {public_url}")
            return public_url
        except Exception as e:
            raise Exception(f"Fallo al alojar imagen temporalmente: {str(e)}")

    def _crear_contenedor(self, image_url: str, caption: str) -> str:
        """Paso 1 de IG: Decirle que prepare la foto desde la URL"""
        url = f"{self.base_url}/{self.ig_user_id}/media"
        
        payload = {
            'image_url': image_url,
            'caption': caption,
            'access_token': self.access_token
        }
        
        resp = requests.post(url, data=payload, timeout=30)
        try:
            resp.raise_for_status()
            return resp.json()['id']
        except Exception as e:
            logger.error(f"Error creando contenedor IG: {resp.text}")
            raise Exception(f"Error IG Step 1: {resp.text}")

    def _publicar_contenedor(self, creation_id: str) -> str:
        """Paso 2 de IG: Publicar lo que preparamos"""
        url = f"{self.base_url}/{self.ig_user_id}/media_publish"
        
        payload = {
            'creation_id': creation_id,
            'access_token': self.access_token
        }
        
        # Esperamos 3 segundos para asegurar que IG procesó la imagen del paso 1
        time.sleep(3)
        
        resp = requests.post(url, data=payload, timeout=30)
        try:
            resp.raise_for_status()
            post_id = resp.json()['id']
            logger.info(f"🎉 ¡Publicado en Instagram! ID: {post_id}")
            return post_id
        except Exception as e:
             logger.error(f"Error publicando contenedor IG: {resp.text}")
             raise Exception(f"Error IG Step 2: {resp.text}")