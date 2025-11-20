"""from abc import ABC, abstractmethod
from typing import Dict, Any


class PublicadorBase(ABC):
    
    def __init__(self, nombre_red: str):
        self.nombre_red = nombre_red
    
    @abstractmethod
    def publicar(self, contenido: Dict[str, Any], access_token: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def obtener_url_oauth(self, redirect_uri: str) -> str:
        pass
    
    @abstractmethod
    def intercambiar_codigo_por_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        pass"""