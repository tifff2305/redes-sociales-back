import requests
import logging
import base64
from typing import List, Dict, Any

from app.config.configuracion import obtener_configuracion
from app.servicios.ia import obtener_servicio_ia # Importamos tu servicio de IA

logger = logging.getLogger(__name__)

class Facebook:
    
    def __init__(self):
        config = obtener_configuracion()
        self.page_id = config.FACEBOOK_PAGE_ID
        self.access_token = config.FACEBOOK_PAGE_ACCESS_TOKEN
        self.base_url = "https://graph.facebook.com/v18.0"
        
        # Instanciamos el servicio de IA para que la clase sea autónoma
        self.ia_service = obtener_servicio_ia()

    # ==================== PUBLICACIÓN DIRECTA (Lo que te faltaba) ====================
    def publicar_foto(self, archivo_binario, mensaje: str) -> str:
        print(f"DEBUG TOKEN: {self.access_token}")
        url = f"{self.base_url}/{self.page_id}/photos"
        
        payload = {
            'message': mensaje,
            'access_token': self.access_token
        }
        
        files = {
            'source': archivo_binario
        }

        try:
            logger.info("📤 Enviando petición a API Graph Facebook...")
            response = requests.post(url, data=payload, files=files, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            post_id = data.get('post_id') or data.get('id')
            
            if not post_id:
                raise ValueError("Facebook no devolvió un ID de publicación.")
                
            logger.info(f"✅ Publicado en FB con ID: {post_id}")
            return post_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión con Facebook: {e}")
            if e.response is not None:
                logger.error(f"Detalle Meta: {e.response.text}")
            raise Exception(f"Fallo en API Facebook: {str(e)}")

    # ==================== PUBLICACIÓN (Lógica Principal) ====================

    def procesar_y_publicar(
        self, 
        texto: str, 
        prompt_imagen: str, 
        hashtags: List[str] = None
    ) -> Dict[str, Any]:
        
        import os
        import time
        
        try:
            logger.info("🚀 Iniciando flujo de publicación automática para Facebook")

            # 1. Preparar Texto
            texto_final = self._preparar_texto(texto, hashtags)
            
            # 2. Generar Imagen con IA
            logger.info(f"🎨 Generando imagen...")
            imagen_data = self.ia_service.generar_imagen(prompt_imagen, quality="standard")
            
            if not imagen_data or "b64_json" not in imagen_data:
                raise ValueError("La IA no retornó una imagen válida.")
                
            # Convertir Base64 a Bytes
            imagen_bytes = base64.b64decode(imagen_data["b64_json"])

            # --- NUEVO: GUARDAR EN DISCO (Igual que TikTok) ---
            output_dir = "outputs"
            os.makedirs(output_dir, exist_ok=True)
            
            # Nombre de archivo único
            timestamp = int(time.time())
            filename = f"facebook_{timestamp}.png"
            file_path = os.path.join(output_dir, filename)
            
            with open(file_path, "wb") as f:
                f.write(imagen_bytes)
                
            logger.info(f"💾 Imagen guardada localmente en: {file_path}")
            # --------------------------------------------------
            
            # 3. Subir a Facebook (usando los bytes que ya tenemos)
            post_id = self._subir_foto_api(imagen_bytes, texto_final)

            return {
                "success": True,
                "publish_id": post_id,
                "message": "Imagen publicada y guardada localmente.",
                "archivo_guardado": file_path,  # Devolvemos la ruta
                "red_social": "facebook",
                "texto_publicado": texto_final
            }

        except Exception as e:
            logger.error(f"❌ Error en flujo Facebook: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "red_social": "facebook"
            }

    # ==================== MÉTODOS PRIVADOS (Helpers) ====================

    def _preparar_texto(self, texto: str, hashtags: List[str]) -> str:
        """Concatena texto y hashtags con el formato correcto"""
        hashtags = hashtags or []
        if not hashtags:
            return texto
            
        # Formateamos hashtags (#Tag) y los unimos
        hashtags_str = " ".join(
            f"#{h.replace('#', '')}" for h in hashtags
        )
        return f"{texto}\n\n{hashtags_str}"

    def _subir_foto_api(self, imagen_bytes: bytes, mensaje: str) -> str:
        """
        Realiza la petición HTTP pura a Graph API.
        Equivalente a _subir_video en tu TikTok.
        """
        url = f"{self.base_url}/{self.page_id}/photos"
        
        payload = {
            'message': mensaje,
            'access_token': self.access_token
        }
        
        files = {
            'source': imagen_bytes
        }

        try:
            logger.info("📤 Enviando petición a API Graph Facebook...")
            response = requests.post(url, data=payload, files=files, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            post_id = data.get('post_id') or data.get('id')
            
            if not post_id:
                raise ValueError("Facebook no devolvió un ID de publicación.")
                
            logger.info(f"✅ Publicado en FB con ID: {post_id}")
            return post_id

        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión con Facebook: {e}")
            if e.response is not None:
                logger.error(f"Detalle Meta: {e.response.text}")
            raise Exception(f"Fallo en API Facebook: {str(e)}")