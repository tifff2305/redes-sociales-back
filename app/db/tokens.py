from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GestorTokens:
    
    tokens_almacenados: Dict[str, Dict[str, Any]] = {}
    verifiers_temporales: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def guardar_verifier(cls, user_id: str, red_social: str, verifier: str) -> None:
        clave = f"{user_id}:{red_social}:verifier"
        cls.verifiers_temporales[clave] = {
            "user_id": user_id,
            "red_social": red_social,
            "verifier": verifier,
            "created_at": datetime.now().isoformat()
        }
        logger.info(f" Verifier guardado: {user_id} - {red_social}")

    @classmethod
    def obtener_verifier(cls, user_id: str, red_social: str) -> Optional[Dict[str, Any]]:
        clave = f"{user_id}:{red_social}:verifier"
        return cls.verifiers_temporales.get(clave)

    @classmethod
    def eliminar_verifier(cls, user_id: str, red_social: str) -> bool:
        clave = f"{user_id}:{red_social}:verifier"
        if clave in cls.verifiers_temporales:
            del cls.verifiers_temporales[clave]
            logger.info(f" Verifier eliminado: {user_id} - {red_social}")
            return True
        return False

    @classmethod
    def guardar_token(
        cls,
        user_id: str,
        red_social: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        
        clave = f"{user_id}:{red_social}"
        
        token_data = {
            "user_id": user_id,
            "red_social": red_social,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "created_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        cls.tokens_almacenados[clave] = token_data
        
        logger.info(f" TOKEN GUARDADO: {user_id} - {red_social}")
        logger.info(f"   Access Token: {access_token[:20]}...")
        return token_data

    @classmethod
    def obtener_token(cls, user_id: str, red_social: str) -> Optional[Dict[str, Any]]:
        clave = f"{user_id}:{red_social}"
        return cls.tokens_almacenados.get(clave)

    @classmethod
    def eliminar_token(cls, user_id: str, red_social: str) -> bool:
        clave = f"{user_id}:{red_social}"
        if clave in cls.tokens_almacenados:
            del cls.tokens_almacenados[clave]
            return True
        return False

    @classmethod
    def usuario_tiene_token(cls, user_id: str, red_social: str) -> bool:
        clave = f"{user_id}:{red_social}"
        return clave in cls.tokens_almacenados