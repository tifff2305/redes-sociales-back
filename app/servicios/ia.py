import json
import logging
from openai import OpenAI
from typing import Dict, Any, List
from functools import lru_cache

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
        
        logger.info(f"✅ Servicio IA inicializado")
    
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
        
        logger.info(f"🚀 Generando contenido para: {', '.join(target_networks)}")
        
        # PASO 1: Generar texto, hashtags y prompts
        contenido_texto = self._generar_texto(contenido, target_networks)
        
        # PASO 2: Generar recursos visuales según la red
        resultado_final = {}
        
        for red in target_networks:
            if red not in contenido_texto:
                continue
            
            data_red = contenido_texto[red].copy()
            
            # Generar imagen para Instagram
            if red == "instagram":
                prompt_imagen = data_red.get("suggested_image_prompt")
                if prompt_imagen:
                    try:
                        logger.info(f"🎨 Generando imagen para Instagram...")
                        imagen_data = self.generar_imagen(prompt_imagen)
                        data_red["imagen_b64"] = imagen_data["b64_json"]
                        logger.info("✅ Imagen generada")
                    except Exception as e:
                        logger.error(f"❌ Error generando imagen: {str(e)}")
            
            # Generar video para TikTok
            if red == "tiktok":
                video_hook = data_red.get("video_hook")
                if video_hook:
                    try:
                        logger.info(f"🎥 Generando video para TikTok...")
                        video_path = f"outputs/{user_id}_tiktok_video.mp4"
                        self.generar_video(video_hook, duracion=4, ruta_salida=video_path)
                        data_red["video_path"] = video_path
                        logger.info("✅ Video generado")
                    except Exception as e:
                        logger.error(f"❌ Error generando video: {str(e)}")
            
            resultado_final[red] = data_red
        
        # Guardar en caché
        self.cache_contenido[user_id] = resultado_final
        
        logger.info(f"✅ Contenido completo generado y guardado en caché")
        
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
            logger.error(f"❌ Error al parsear JSON: {str(e)}")
            raise ValueError(f"Error al parsear respuesta de IA: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error al generar contenido: {str(e)}")
            raise ValueError(f"Error al generar contenido: {str(e)}")
    
    def generar_imagen(
        self,
        prompt: str,
        size: str = "1024x1024"
    ) -> Dict[str, Any]:
        
        try:
            respuesta = self.client.images.generate(
                model=self.modelo_imagen,
                prompt=prompt,
                size=size,
                response_format="b64_json"
            )
            
            resultado = {
                "b64_json": respuesta.data[0].b64_json,
                "prompt_usado": prompt,
                "size": size
            }
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error al generar imagen: {str(e)}")
            raise ValueError(f"Error al generar imagen: {str(e)}")
    
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
            
            logger.info(f"🎥 Iniciando generación de video (Sora)...")

            # 1. Crear el trabajo (Recuerda: seconds debe ser STRING)
            video = self.client.videos.create(
                model=self.modelo_video, 
                prompt=texto,
                seconds=str(duracion) # <--- El arreglo del error 400 anterior
            )
            
            logger.info(f"🆔 Trabajo creado: {video.id}")
            
            # 2. Loop de espera
            while video.status in ["in_progress", "queued"]:
                video = self.client.videos.retrieve(video.id)
                progreso = getattr(video, 'progress', 0) or 0

                estado_icon = "⏳" if video.status == "queued" else "🔄"
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
            logger.info("⬇️ Intentando descargar video...")
            content_bytes = None

            # ESTRATEGIA A: Método download_content (Similar a Node.js)
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
                logger.error(f"❌ No se encontró método de descarga. Métodos disponibles: {dir(self.client.videos)}")
                raise ValueError("La librería no tiene un método conocido para descargar el video.")

            # 4. Guardar en disco
            if content_bytes:
                with open(ruta_salida, "wb") as archivo:
                    archivo.write(content_bytes)
                logger.info(f"✅ Video guardado exitosamente: {ruta_salida}")
                return ruta_salida
            else:
                raise ValueError("No se pudieron obtener los bytes del video.")
            
        except Exception as e:
            logger.error(f"❌ Error generando video: {str(e)}")
            # IMPORTANTE: Devolvemos string vacío para que no rompa todo el flujo del endpoint
            # y al menos te llegue el texto generado.
            return ""


@lru_cache()
def obtener_servicio_ia() -> ServicioIA:
    return ServicioIA()