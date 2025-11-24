from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

# Usamos tus clases nuevas (sin base de datos SQL)
from app.repositorios.tokens import GestorTokens
from app.plataformas.tiktok import TikTok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="")

# ==================== 1. ENDPOINT PARA BOTÓN MANUAL (Opcional) ====================
@router.get("/tiktok/conectar")
async def conectar_tiktok(
    user_id: str = Query(..., description="ID del usuario")
):
    try:
        tiktok_service = TikTok()
        
        # Obtenemos URL y el Verificador de seguridad
        auth_url, verifier = tiktok_service.obtener_url_oauth_con_verifier(user_id)
        
        # IMPORTANTE: Guardar el verifier temporalmente
        GestorTokens.guardar_verifier(
            user_id=user_id,
            red_social="tiktok",
            verifier=verifier
        )
        
        return {
            "auth_url": auth_url,
            "mensaje": "Redirige al usuario a esta URL para autorizar"
        }
    except Exception as e:
        logger.error(f"Error iniciando OAuth TikTok: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 2. CALLBACK (OBLIGATORIO) ====================
# TikTok redirigirá aquí después de que el usuario acepte
@router.get("/tiktok/login")
async def login_tiktok(user_id: str = Query("api-user")):
    """
    🔗 Endpoint simple: Genera URL de login y guarda verifier
    El usuario abre esta URL, autoriza, y el callback guarda el token
    """
    try:
        from app.plataformas.tiktok import TikTok
        from app.repositorios.tokens import GestorTokens
        
        tiktok = TikTok()
        
        # Generar URL y verifier
        auth_url, verifier = tiktok.obtener_url_oauth_con_verifier(user_id)
        
        # Guardar verifier
        GestorTokens.guardar_verifier(user_id, "tiktok", verifier)
        
        return {
            "auth_url": auth_url,
            "mensaje": "Abre esta URL para autorizar TikTok"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tiktok/callback")
async def callback_tiktok(
    code: str = Query(...),
    state: str = Query(None)
):
    """
    Callback automático de TikTok (guarda el token)
    """
    try:
        from app.plataformas.tiktok import TikTok
        from app.repositorios.tokens import GestorTokens
        
        user_id = state or "api-user"
        tiktok = TikTok()
        
        # Recuperar verifier
        verifier_data = GestorTokens.obtener_verifier(user_id, "tiktok")
        if not verifier_data:
            raise HTTPException(status_code=400, detail="Error: verifier no encontrado")
        
        # Canjear código por token
        token_data = tiktok.intercambiar_codigo_por_token(code, verifier_data['verifier'])
        
        # GUARDAR TOKEN
        GestorTokens.guardar_token(
            user_id=user_id,
            red_social="tiktok",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data.get("expires_in"),
            metadata={"open_id": token_data.get("open_id")}
        )
        
        # Limpiar verifier
        GestorTokens.eliminar_verifier(user_id, "tiktok")
        
        return {"success": True, "mensaje": "TikTok conectado! Cierra esta ventana"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/facebook/callback")
async def callback_facebook(
    code: str = Query(...),
    state: str = Query(None)
):
    """Callback de OAuth Facebook"""
    # TODO: Implementar
    raise HTTPException(
        status_code=501,
        detail="Facebook OAuth no implementado aún"
    )


# ==================== INSTAGRAM ====================

@router.get("/instagram/conectar")
async def conectar_instagram(user_id: str = Query(...)):
    """Inicia flujo OAuth de Instagram"""
    # TODO: Implementar
    raise HTTPException(
        status_code=501,
        detail="Instagram OAuth no implementado aún"
    )


@router.get("/instagram/callback")
async def callback_instagram(
    code: str = Query(...),
    state: str = Query(None)
):
    """Callback de OAuth Instagram"""
    # TODO: Implementar
    raise HTTPException(
        status_code=501,
        detail="Instagram OAuth no implementado aún"
    )


# ==================== TOKENS ====================

@router.get("/tokens/{user_id}")
async def obtener_tokens_usuario(
    user_id: str,

):
    """
    Obtiene estado de tokens de un usuario.
    Muestra qué redes tiene conectadas.
    """
    repo_tokens = GestorTokens()
    redes = ["tiktok", "facebook", "instagram", "linkedin", "whatsapp"]
    
    tokens_activos = []
    for red in redes:
        if repo_tokens.usuario_tiene_token(user_id, red):
            tokens_activos.append(red)
    
    return {
        "user_id": user_id,
        "redes_conectadas": tokens_activos
    }