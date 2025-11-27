import json
import logging
from openai import OpenAI
from typing import Dict, Any, List
from functools import lru_cache
import os
import base64
import time
import requests

from app.config.configuracion import obtener_configuracion
from app.utilidades.prompt import obtener_prompt

logger = logging.getLogger(__name__)

class ServicioIA:
    
    _instancia = None
    
    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
            cls._instancia._inicializado = False
        return cls._instancia
    
    def __init__(self):
        if self._inicializado:
            return
        
        config = obtener_configuracion()
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.modelo_texto = config.MODELO_TEXTO
        self.modelo_imagen = config.MODELO_IMAGEN
        self.modelo_video = config.MODELO_VIDEO
        self.cache_contenido: Dict[str, Dict[str, Any]] = {}
        self._inicializado = True
        
        logger.info(f" Servicio IA inicializado")
    
    def generar_contenido_completo(
        self,
        user_id: str,
        contenido: str,
        target_networks: List[str]
    ) -> Dict[str, Any]:
        
        redes_validas = ["facebook", "instagram", "linkedin", "tiktok", "whatsapp"]
        redes_invalidas = [red for red in target_networks if red not in redes_validas]
        
        if redes_invalidas:
            raise ValueError(f"Redes inválidas: {redes_invalidas}")
        
        if not target_networks:
            raise ValueError("Especifica al menos una red social")
        
        logger.info(f" Generando contenido para: {', '.join(target_networks)}")
        
        # PASO 1: Generar texto, hashtags y prompts
        contenido_texto = self._generar_texto(contenido, target_networks)
        
        # PASO 2: Generar recursos visuales según la red
        resultado_final = {}
        
        # Crear carpeta outputs si no existe
        os.makedirs("outputs", exist_ok=True)

        for red in target_networks:
            if red not in contenido_texto:
                continue
            
            data_red = contenido_texto[red].copy()
            
            # === GENERACIÓN DE IMAGEN (Facebook, Instagram, LinkedIn, WhatsApp) ===
            if red in ["facebook", "instagram", "whatsapp", "linkedin"]:
                # 1. Intentamos obtener el prompt sugerido por la IA
                prompt_imagen = data_red.get("suggested_image_prompt")
                
                # 2. FALLBACK: Si la IA olvidó el prompt, usamos el texto del post (cortado a 300 chars)
                if not prompt_imagen:
                    texto_post = data_red.get("text", "")
                    if texto_post:
                        prompt_imagen = f"A professional photorealistic image representing: {texto_post[:300]}"
                        logger.warning(f"⚠️ IA no dio prompt para {red}, usando texto como fallback.")

                # 3. Solo si tenemos prompt (que ahora casi siempre tendremos), generamos
                if prompt_imagen:
                    try:
                        logger.info(f"🎨 Generando imagen para {red}...")
                        
                        imagen_bytes = self.generar_imagen(prompt_imagen)
                        
                        if imagen_bytes:
                            timestamp = int(time.time())
                            # Usamos os.path.join para evitar problemas de slash en Windows
                            nombre_archivo = f"{user_id}_{red}_{timestamp}.png"
                            ruta_archivo = os.path.join("outputs", nombre_archivo)
                            
                            with open(ruta_archivo, "wb") as f:
                                f.write(imagen_bytes)
                                
                            data_red["image_path"] = ruta_archivo
                            logger.info(f"✅ Imagen guardada en: {ruta_archivo}")
                        else:
                            logger.error(f"❌ La IA no retornó datos válidos para {red}.")

                    except Exception as e:
                        logger.error(f"❌ Error generando imagen {red}: {str(e)}")
            
            # Generar video para TikTok
            if red == "tiktok":
                video_hook = data_red.get("video_hook")
                if video_hook:
                    try:
                        logger.info(f" Generando video para TikTok...")
                        video_path = f"outputs/{user_id}_tiktok_video.mp4"
                        self.generar_video(video_hook, duracion=4, ruta_salida=video_path)
                        data_red["video_path"] = video_path
                        logger.info(" Video generado")
                    except Exception as e:
                        logger.error(f" Error generando video: {str(e)}")
            
            resultado_final[red] = data_red
        
        # Guardar en caché
        self.cache_contenido[user_id] = resultado_final
        
        logger.info(f" Contenido completo generado y guardado en caché")
        
        return resultado_final
    
    def _generar_texto(
        self,
        contenido: str,
        redes_sociales: List[str]
    ) -> Dict[str, Any]:
        
        mensaje_usuario = f"""Contenido: {contenido}
Redes sociales: {', '.join(redes_sociales)}

Genera contenido optimizado para cada red social solicitada."""
        
        try:
            respuesta = self.client.chat.completions.create(
                model=self.modelo_texto,
                messages=[
                    {"role": "system", "content": obtener_prompt()},
                    {"role": "user", "content": mensaje_usuario}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=3000,
                timeout=1000
            )
            
            contenido_generado = json.loads(respuesta.choices[0].message.content)
            
            return contenido_generado
            
        except json.JSONDecodeError as e:
            logger.error(f" Error al parsear JSON: {str(e)}")
            raise ValueError(f"Error al parsear respuesta de IA: {str(e)}")
        except Exception as e:
            logger.error(f" Error al generar contenido: {str(e)}")
            raise ValueError(f"Error al generar contenido: {str(e)}")
    
    def generar_imagen(
        self,
        prompt: str,
        size: str = "1024x1024"
    ) -> bytes:
        """
        Replica la lógica de generarImagen.js:
        1. Intenta obtener b64_json.
        2. Si no, intenta obtener URL y descargarla.
        Retorna: Bytes de la imagen listos para guardar.
        """
        try:
            logger.info(f" Generando imagen con modelo: {self.modelo_imagen}")
            
            # Configuración de parámetros
            # NOTA: En tu JS comentaste que 'response_format' daba error con gpt-image-1,
            # pero el modelo suele devolver b64 por defecto.
            # Aquí lo hacemos dinámico: si es gpt-4 o dall-e-3 estándar, pedimos b64.
            # Si es tu modelo custom, dejamos que la API decida y nosotros parseamos la respuesta.
            
            params = {
                "model": self.modelo_imagen,
                "prompt": prompt,
                "size": size,
                "n": 1,
            }

            # Si NO es tu modelo custom raro, forzamos b64 para asegurar (DALL-E 3 lo requiere)
            if "gpt-image-1" not in self.modelo_imagen:
                params["response_format"] = "b64_json"

            # Llamada a OpenAI
            respuesta = self.client.images.generate(**params)
            
            # --- LÓGICA DE DETECCIÓN (INTENTO 1 y INTENTO 2 del JS) ---
            data_obj = respuesta.data[0]
            
            # 1. Buscar b64_json
            imagen_b64 = getattr(data_obj, 'b64_json', None)
            
            if imagen_b64:
                logger.info("✅ Imagen recibida en Base64")
                return base64.b64decode(imagen_b64)
            
            # 2. Buscar URL (Fallback)
            imagen_url = getattr(data_obj, 'url', None)
            
            if imagen_url:
                logger.info(f"🔗 Imagen recibida como URL, descargando... {imagen_url[:30]}...")
                resp_img = requests.get(imagen_url)
                resp_img.raise_for_status()
                logger.info("✅ Imagen descargada correctamente")
                return resp_img.content

            raise ValueError("La API respondió, pero no se encontró ni 'b64_json' ni 'url'.")
            
        except Exception as e:
            logger.error(f"❌ Error crítico en generar_imagen: {str(e)}")
            # Si quieres ver el error crudo como en el JS:
            if hasattr(e, 'response'):
                 logger.error(f"Response raw: {e.response}")
            raise ValueError(f"Fallo generación imagen: {str(e)}")
    
    def generar_video(
        self,
        texto: str,
        duracion: int = 4,
        ruta_salida: str = "outputs/video.mp4"
    ) -> str:
        
        import time
        import os
        import requests # Necesitaremos esto por si nos devuelve una URL
        
        try:
            os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
            
            logger.info(f" Iniciando generación de video (Sora)...")

            # 1. Crear el trabajo (Recuerda: seconds debe ser STRING)
            video = self.client.videos.create(
                model=self.modelo_video, 
                prompt=texto,
                seconds=str(duracion)
            )
            
            logger.info(f" Trabajo creado: {video.id}")
            
            # 2. Loop de espera
            while video.status in ["in_progress", "queued"]:
                video = self.client.videos.retrieve(video.id)
                progreso = getattr(video, 'progress', 0) or 0

                estado_icon = "" if video.status == "queued" else ""
                logger.info(f"{estado_icon} [Sora] Estado: {video.status.upper()} | Progreso: {progreso}%")
                
                time.sleep(4)
                
                # Barra de progreso visual
                largo_barra = 20
                llenado = int((progreso / 100) * largo_barra)
                barra = "=" * llenado + "-" * (largo_barra - llenado)
                print(f"\rProcesando: [{barra}] {progreso:.1f}%", end="", flush=True)
                
                time.sleep(2)
            
            print() # Salto de línea
            
            if video.status == "failed":
                error_msg = getattr(video, 'error', 'Error desconocido')
                raise ValueError(f"Generación fallida: {error_msg}")

            # 3. INTENTOS DE DESCARGA (La parte crítica)
            logger.info("⬇ Intentando descargar video...")
            content_bytes = None

            # ESTRATEGIA A: Método download_content 
            if hasattr(self.client.videos, 'download_content'):
                logger.info("   > Usando método download_content...")
                response = self.client.videos.download_content(video.id)
                # Si es una respuesta HTTP, leemos los bytes. Si son bytes directos, los usamos.
                content_bytes = response.read() if hasattr(response, 'read') else response

            # ESTRATEGIA B: Verificar si el objeto video ya tiene la URL (Común en betas)
            elif hasattr(video, 'result_url') or hasattr(video, 'url'):
                url = getattr(video, 'result_url', getattr(video, 'url', None))
                if url:
                    logger.info(f"   > Descargando desde URL: {url[:30]}...")
                    resp = requests.get(url)
                    content_bytes = resp.content

            # ESTRATEGIA C: Método content (El que falló antes, por si acaso)
            elif hasattr(self.client.videos, 'content'):
                logger.info("   > Usando método content...")
                response = self.client.videos.content(video.id)
                content_bytes = response.read() if hasattr(response, 'read') else response.content
            
            else:
                # Si todo falla, imprimimos ayuda para depurar
                logger.error(f" No se encontró método de descarga. Métodos disponibles: {dir(self.client.videos)}")
                raise ValueError("La librería no tiene un método conocido para descargar el video.")

            # 4. Guardar en disco
            if content_bytes:
                with open(ruta_salida, "wb") as archivo:
                    archivo.write(content_bytes)
                logger.info(f" Video guardado exitosamente: {ruta_salida}")
                return ruta_salida
            else:
                raise ValueError("No se pudieron obtener los bytes del video.")
            
        except Exception as e:
            logger.error(f" Error generando video: {str(e)}")
            # IMPORTANTE: Devolvemos string vacío para que no rompa todo el flujo del endpoint
            # y al menos te llegue el texto generado.
            return ""


@lru_cache()
def obtener_servicio_ia() -> ServicioIA:
    return ServicioIA()