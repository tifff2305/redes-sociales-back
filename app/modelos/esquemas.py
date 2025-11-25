from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Any, Optional

# --- LO NUEVO: Para Autenticación ---
class UsuarioRegistro(BaseModel):
    nombre: str
    email: EmailStr
    password: str

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    usuario: str

class SolicitudGenerarContenido(BaseModel):
    """Request para generar contenido"""
    contenido: str = Field(..., min_length=10, description="Contenido base")
    target_networks: List[str] = Field(..., description="Redes sociales objetivo")
    user_id: str = Field(default="api-user", description="ID del usuario")
    
    class Config:
        json_schema_extra = {
            "example": {
                "contenido": "Lanzamos característica para gestionar trámites",
                "target_networks": ["tiktok", "facebook"],
                "user_id": "usuario123"
            }
        }

class RespuestaContenido(BaseModel):
    """Response de contenido generado"""
    user_id: str
    contenido: Dict[str, Any]


class SolicitudPublicar(BaseModel):
    """Request para publicar contenido"""
    user_id: str
    red_social: str
    texto: Optional[str] = None
    usar_cache: bool = True


class RespuestaPublicacion(BaseModel):
    """Response de publicación"""
    success: bool
    red_social: str
    post_id: Optional[str] = None
    publish_id: Optional[str] = None
    message: str


class RespuestaOAuth(BaseModel):
    """Response de OAuth"""
    auth_url: Optional[str] = None
    success: Optional[bool] = None
    user_id: Optional[str] = None
    mensaje: str