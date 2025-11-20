"""from typing import Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GeneracionContenido:
    
    historial_generaciones: List[Dict[str, Any]] = []

    @classmethod
    def guardar_generacion(cls, user_id: str, prompt: str, ai_model_used: str, results: Dict[str, Any]) -> Dict[str, Any]:
        
        registro = {
            "id": len(cls.historial_generaciones) + 1,
            "user_id": user_id,
            "prompt_original": prompt,
            "ai_model_used": ai_model_used,
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        
        cls.historial_generaciones.append(registro)
        
        logger.info(f" Simulación DB: Registro #{registro['id']} Guardado")
        logger.info(f"   Contenidos generados: {', '.join(results.keys())}")

        return registro"""