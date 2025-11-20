"""import json
import logging
from openai import OpenAI
from typing import Dict, Any, List
from app.utilidades.prompt import obtener_prompt
from app.db.modelos import GeneracionContenido

logger = logging.getLogger(__name__)


class ServicioContenido:
    
    REDES_VALIDAS = ["facebook", "instagram", "linkedin", "tiktok", "whatsapp"]
    
    def __init__(self, openai_client: OpenAI, modelo_ia: str = "gpt-4o-mini"):
        self.openai_client = openai_client
        self.modelo_ia = modelo_ia
        self.cache_contenido: Dict[str, Dict[str, Any]] = {}
    
    def generar_y_guardar(
        self,
        user_id: str,
        contenido: str,
        target_networks: List[str]
    ) -> Dict[str, Any]:
        
        redes_invalidas = [red for red in target_networks if red not in self.REDES_VALIDAS]
        if redes_invalidas:
            raise ValueError(f"Redes inválidas: {redes_invalidas}. Válidas: {self.REDES_VALIDAS}")
        
        if not target_networks:
            raise ValueError("Debes especificar al menos una red social")
        
        logger.info(f"🚀 Generando contenido para: {', '.join(target_networks)}")
        
        mensaje_usuario = f"""Contenido: {contenido}
Redes sociales: {', '.join(target_networks)}

Genera contenido optimizado para cada red social solicitada."""
        
        try:
            respuesta = self.openai_client.chat.completions.create(
                model=self.modelo_ia,
                messages=[
                    {"role": "system", "content": obtener_prompt()},
                    {"role": "user", "content": mensaje_usuario}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=3000,
                timeout=30
            )
            
            contenido_generado = json.loads(respuesta.choices[0].message.content)
            
            try:
                GeneracionContenido.guardar_generacion(
                    user_id=user_id,
                    prompt=contenido,
                    ai_model_used=self.modelo_ia,
                    results=contenido_generado
                )
                logger.info("💾 Contenido guardado en DB")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo guardar en DB: {e}")
            
            self.cache_contenido[user_id] = contenido_generado
            logger.info(f"✅ Contenido guardado en caché para user_id: {user_id}")
            
            return contenido_generado
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error al parsear JSON: {str(e)}")
            raise ValueError(f"Error al parsear JSON: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error al generar contenido: {str(e)}")
            raise ValueError(f"Error al generar contenido: {str(e)}")
    
    def obtener_de_cache(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self.cache_contenido:
            raise ValueError(f"No hay contenido en caché para user_id: {user_id}")
        return self.cache_contenido[user_id]"""