from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import logging

# IMPORTAMOS LA SEGURIDAD PARA OBTENER EL USUARIO REAL
from app.utilidades.dependencia import obtener_usuario_actual
from app.modelos.tablas import Usuario

from app.repositorios.tokens import GestorTokens
from app.plataformas.tiktok import TikTok
from app.config.bd import SessionLocal # Necesario para guardar el token en el callback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="")

# Helper para obtener BD manualmente dentro del callback
def obtener_bd_manual():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



# ==================== TOKENS (ESTADO) ====================
# Quitamos {user_id} de la URL. Ahora es solo /tokens/estado
@router.get("/tokens/estado")
async def obtener_tokens_usuario(
    # Obtenemos el usuario del token (Header Authorization)
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(obtener_bd_manual) # O usa tu dependency normal 'obtener_bd'
):
    """
    Verifica qué redes tiene conectadas el usuario logueado.
    """
    user_id = usuario_actual.id # ID real (ej: 1)
    
    repo_tokens = GestorTokens()
    redes = ["tiktok", "facebook", "instagram", "linkedin", "whatsapp"]
    
    tokens_activos = []
    
    # IMPORTANTE: Asegúrate de pasar la sesión de BD 'db' si tu función lo pide.
    # Si tu GestorTokens.usuario_tiene_token usa una sesión interna, está bien,
    # pero según tu código anterior, 'usuario_tiene_token' pide 'db'.
    
    for red in redes:
        # Pasamos el ID entero (1), no el string "api-user"
        if repo_tokens.usuario_tiene_token(db, user_id, red):
            tokens_activos.append(red)
    
    return {
        "user_id": user_id,
        "redes_conectadas": tokens_activos
    }

# ==================== 1. INICIAR CONEXIÓN ====================
@router.get("/tiktok/conectar")
async def conectar_tiktok(
    usuario_actual: Usuario = Depends(obtener_usuario_actual)
):
    try:
        user_id_str = str(usuario_actual.id)
        tiktok_service = TikTok()
        
        # 1. Obtenemos URL y Verifier
        auth_url, verifier = tiktok_service.obtener_url_oauth_con_verifier(user_id_str)
        
        # 2. Guardamos el verifier asociado a este ID real
        GestorTokens.guardar_verifier(
            user_id=user_id_str,
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


# ==================== 2. CALLBACK ====================
@router.get("/tiktok/callback")
async def callback_tiktok(
    code: str = Query(...),
    state: str = Query(None) # Aquí llega el user_id dinámico
):
    try:
        # Validamos que venga el state (que es tu user_id)
        if not state:
             raise HTTPException(status_code=400, detail="Falta el parámetro state (user_id)")

        user_id = state 
        tiktok = TikTok()
        
        # --- CORRECCIÓN AQUÍ ---
        # obtener_verifier devuelve el string directamente, NO un diccionario.
        verifier = GestorTokens.obtener_verifier(user_id, "tiktok")
        
        if not verifier:
            raise HTTPException(status_code=400, detail="Error: verifier no encontrado o expiró")
        
        # Usamos la variable 'verifier' directamente (antes decía verifier['verifier'])
        token_data = tiktok.intercambiar_codigo_por_token(code, verifier)
        
        # GUARDAR TOKEN (Usando el user_id que llegó en el state)
        GestorTokens.guardar_token(
            db=next(obtener_bd_manual()),
            user_id=int(user_id),
            red_social="tiktok",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data.get("expires_in"),
            # metadata={"open_id": token_data.get("open_id")} # Descomenta si tu función lo soporta
        )
        
        # Limpiar verifier usado
        GestorTokens.eliminar_verifier(user_id, "tiktok")
        
        # Redirigir al frontend (ajusta el puerto si es necesario)
        return RedirectResponse(url="http://localhost:4200/chat")
        
    except Exception as e:
        logger.error(f"Error Callback TikTok: {e}")
        # Retornamos el error en JSON para verlo en el navegador si falla
        return {"error": "Fallo en callback", "detalle": str(e)}