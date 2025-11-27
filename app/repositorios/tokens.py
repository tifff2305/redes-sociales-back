from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from app.modelos.tablas import TokenRedSocial

logger = logging.getLogger(__name__)

class GestorTokens:
    
    # Los verifiers son temporales (duran segundos), los dejamos en memoria RAM
    verifiers_temporales: Dict[str, Dict[str, Any]] = {}

    # ==========================================
    # 1. MÉTODOS PARA VERIFIERS (Memoria)
    # ==========================================
    @classmethod
    def guardar_verifier(cls, user_id: int, red_social: str, verifier: str) -> None:
        clave = f"{user_id}:{red_social}"
        cls.verifiers_temporales[clave] = {
            "verifier": verifier,
            "created_at": datetime.now()
        }
        logger.info(f"🔐 Verifier temporal guardado para: {user_id} - {red_social}")

    @classmethod
    def obtener_verifier(cls, user_id: int, red_social: str) -> Optional[str]:
        clave = f"{user_id}:{red_social}"
        data = cls.verifiers_temporales.get(clave)
        if data:
            return data.get("verifier")
        return None

    @classmethod
    def eliminar_verifier(cls, user_id: int, red_social: str):
        clave = f"{user_id}:{red_social}"
        if clave in cls.verifiers_temporales:
            del cls.verifiers_temporales[clave]

    # ==========================================
    # 2. MÉTODOS PARA TOKENS (Base de Datos)
    # ==========================================
    
    @classmethod
    def guardar_token(
        cls,
        db: Session,  # <--- Nuevo parámetro obligatorio
        user_id: int,
        red_social: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None, # Segundos de vida
    ) -> Dict[str, Any]:
        
        # 1. Calcular fecha de expiración si nos dan segundos
        fecha_exp = None
        if expires_in:
            fecha_exp = datetime.now() + timedelta(seconds=expires_in)

        # 2. Buscar si ya existe un token para este usuario y red
        token_db = db.query(TokenRedSocial).filter_by(
            usuario_id=user_id, 
            red_social=red_social
        ).first()

        if token_db:
            # --- ACTUALIZAR EXISTENTE ---
            logger.info(f"🔄 Actualizando token existente para {red_social}...")
            token_db.token_acceso = access_token
            # Solo actualizamos refresh_token si viene uno nuevo (a veces las APIs no lo devuelven siempre)
            if refresh_token:
                token_db.token_refresh = refresh_token
            token_db.fecha_expiracion = fecha_exp
        else:
            # --- CREAR NUEVO ---
            logger.info(f"✨ Creando nuevo token para {red_social}...")
            token_db = TokenRedSocial(
                usuario_id=user_id,
                red_social=red_social,
                token_acceso=access_token,
                token_refresh=refresh_token,
                fecha_expiracion=fecha_exp
            )
            db.add(token_db)

        # 3. Guardar cambios en Postgres
        db.commit()
        db.refresh(token_db)

        # Devolvemos formato diccionario para compatibilidad
        return {
            "access_token": token_db.token_acceso,
            "refresh_token": token_db.token_refresh,
            "expires_at": token_db.fecha_expiracion
        }

    @classmethod
    def obtener_token(cls, db: Session, user_id: int, red_social: str) -> Optional[Dict[str, Any]]:
        """Retorna el token en formato diccionario o None si no existe"""
        token_db = db.query(TokenRedSocial).filter_by(
            usuario_id=user_id, 
            red_social=red_social
        ).first()

        if not token_db:
            return None
            
        return {
            "access_token": token_db.token_acceso,
            "refresh_token": token_db.token_refresh,
            "expires_at": token_db.fecha_expiracion
        }

    @classmethod
    def usuario_tiene_token(cls, db: Session, user_id: int, red_social: str) -> bool:
        """Verifica rápidamente si existe el registro"""
        count = db.query(TokenRedSocial).filter_by(
            usuario_id=user_id, 
            red_social=red_social
        ).count()
        return count > 0