"""import json
import logging
from openai import OpenAI
from typing import Dict, Any, List
from app.utilidades.prompt import obtener_prompt

logger = logging.getLogger(__name__)


class GeneradorContenido:
    
    def __init__(self, openai_client: OpenAI, modelo_db=None, modelo_ia: str = "gpt-4o-mini"):
        self.modelo_ia = modelo_ia
        self.modelo_db = modelo_db
        self.openai_client = openai_client
        self.redes_validas = ["facebook", "instagram", "linkedin", "tiktok", "whatsapp"]

    def generar_y_guardar_contenido(
        self,
        user_id: str,
        contenido: str,
        target_networks: List[str]
    ) -> Dict[str, Any]:
        
        redes_invalidas = [red for red in target_networks if red not in self.redes_validas]
        if redes_invalidas:
            raise ValueError(f"Redes inválidas: {redes_invalidas}. Válidas: {self.redes_validas}")
        
        if not target_networks:
            raise ValueError("Debes especificar al menos una red social")
        
        logger.info(f" Generando contenido para: {', '.join(target_networks)}")
        
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
            
            # Log para verificar el contenido generado antes de enviarlo
            logger.debug(f"Contenido generado: {json.dumps(contenido_generado, ensure_ascii=False, indent=2)}")
            
            if self.modelo_db:
                try:
                    self.modelo_db.guardar_generacion(
                        user_id=user_id,
                        prompt=contenido,
                        ai_model_used=self.modelo_ia,
                        results=contenido_generado
                    )
                    logger.info(" Contenido guardado en DB")
                except Exception as e:
                    logger.warning(f" No se pudo guardar en DB: {e}")
            
            logger.info(" Generación completada exitosamente")
            return contenido_generado
            
        except json.JSONDecodeError as e:
            logger.error(f" Error al parsear JSON: {str(e)}")
            raise ValueError(f"Error al parsear JSON: {str(e)}")
        except Exception as e:
            logger.error(f" Error al generar contenido: {str(e)}")
            raise ValueError(f"Error al generar contenido: {str(e)}")"""