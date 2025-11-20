"""from fastapi import APIRouter, HTTPException, Query
from app.core.servicios.NServicio.oauth import ServicioOAuth
from app.plataformas.tiktok import TikTok as PublicadorTikTok
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="")

TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "https://epifania-nonideological-amie.ngrok-free.dev/tiktok/callback")
FACEBOOK_REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI", "https://epifania-nonideological-amie.ngrok-free.dev/facebook/callback")

servicio_oauth = ServicioOAuth(
    tiktok_redirect_uri=TIKTOK_REDIRECT_URI,
    facebook_redirect_uri=FACEBOOK_REDIRECT_URI
)


@router.get("/tiktok/conectar")
async def conectar_tiktok(user_id: str = Query(...)):
    return servicio_oauth.iniciar_tiktok(user_id)


@router.get("/tiktok/callback")
async def callback_tiktok(
    code: str = Query(...), 
    state: str = Query(None)
):
    try:
        return servicio_oauth.callback_tiktok(code, state)
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}")
        logger.error("="*80 + "\n")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/facebook/conectar")
async def conectar_facebook(user_id: str = Query(...)):
    return servicio_oauth.iniciar_facebook(user_id)


@router.get("/facebook/callback")
async def callback_facebook(
    code: str = Query(...), 
    state: str = Query(None)
):
    try:
        return servicio_oauth.callback_facebook(code, state)
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}")
        logger.error("="*80 + "\n")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens/{user_id}")
async def obtener_tokens_usuario(user_id: str):
    return servicio_oauth.obtener_estado_tokens(user_id)"""