from typing import Dict, Any, List
from datetime import datetime

# Definición de la estructura de la tabla CONTENT_GENERATIONS
class GeneracionContenido:
    """Simulación del Modelo ORM para la tabla CONTENT_GENERATIONS."""
    
    # Lista estática para almacenar los registros simulados en memoria
    historial_generaciones: List[Dict[str, Any]] = []

    @classmethod
    def guardar_generacion(cls, user_id: str, topic_name: str, prompt: str, ai_model_used: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simula la inserción de una nueva fila en la BD.
        Retorna el registro creado.
        """
        
        registro = {
            "id": len(cls.historial_generaciones) + 1,
            "user_id": user_id,
            "topic_name": topic_name,
            "prompt_original": prompt,
            "ai_model_used": ai_model_used,
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        
        cls.historial_generaciones.append(registro)
        
        # Reporte de consola de la simulación
        print(f"--- 💾 Simulación DB: Registro #{registro['id']} Guardado ---")
        print(f"Tema: {topic_name} | Modelo: {ai_model_used}")
        print(f"Contenidos generados: {', '.join(results.keys())}")
        print("----------------------------------------------------------")

        return registro