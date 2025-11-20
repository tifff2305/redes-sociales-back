import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.modelos.tablas import GeneracionContenido

logger = logging.getLogger(__name__)


class RepositorioContenido:
    
    def __init__(self, db_session: Session = None):
        self.db = db_session
    
    def guardar_generacion(
        self,
        user_id: str,
        prompt: str,
        ai_model_usado: str,
        resultados: Dict[str, Any]
    ) -> GeneracionContenido:
 
        if not self.db:
            raise ValueError("Sesión de BD no disponible")
        
        generacion = GeneracionContenido(
            user_id=user_id,
            prompt_original=prompt,
            ai_model_usado=ai_model_usado,
            resultados=resultados
        )
        
        self.db.add(generacion)
        self.db.commit()
        self.db.refresh(generacion)
        
        logger.info(f"Generación guardada en BD. ID: {generacion.id}")
        
        return generacion
    
    def obtener_ultima_generacion(self, user_id: str) -> Optional[GeneracionContenido]:
 
        if not self.db:
            return None
        
        return self.db.query(GeneracionContenido)\
            .filter(GeneracionContenido.user_id == user_id)\
            .order_by(GeneracionContenido.created_at.desc())\
            .first()
    
    def obtener_generaciones_usuario(
        self,
        user_id: str,
        limit: int = 10
    ) -> list:
 
        if not self.db:
            return []
        
        return self.db.query(GeneracionContenido)\
            .filter(GeneracionContenido.user_id == user_id)\
            .order_by(GeneracionContenido.created_at.desc())\
            .limit(limit)\
            .all()