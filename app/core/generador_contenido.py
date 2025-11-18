import json
import logging
from openai import OpenAI
from typing import Dict, Any, List
from app.core.prompt import obtener_prompt

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
        
        logger.info(f"Generando contenido para: {', '.join(target_networks)}")
        
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
                max_tokens=3000
            )
            
            contenido_generado = json.loads(respuesta.choices[0].message.content)
            
            if self.modelo_db:
                try:
                    self.modelo_db.guardar_generacion(
                        user_id=user_id,
                        prompt=contenido,
                        ai_model_used=self.modelo_ia,
                        results=contenido_generado
                    )
                except Exception as e:
                    print(f" No se pudo guardar en DB: {e}")
            
            print(" Generación completada")
            return contenido_generado
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Error al parsear JSON: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error al generar contenido: {str(e)}")