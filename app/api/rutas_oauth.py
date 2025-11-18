from fastapi import APIRouter, HTTPException, Query
from app.core.servicios.tiktok import PublicadorTikTok
from app.core.servicios.facebook import PublicadorFacebook
from app.db.tokens import GestorTokens
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="")

# Las URI deben estar en el .env, pero las dejamos aquí para la prueba.
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "https://epifania-nonideological-amie.ngrok-free.dev/tiktok/callback")
FACEBOOK_REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI", "https://epifania-nonideological-amie.ngrok-free.dev/facebook/callback")


@router.get("/tiktok/conectar")
async def conectar_tiktok(user_id: str = Query(...)):
    publicador = PublicadorTikTok()
    auth_url, verifier = publicador.obtener_url_oauth_con_verifier(TIKTOK_REDIRECT_URI, user_id)
    
    GestorTokens.guardar_verifier(user_id=user_id, red_social="tiktok", verifier=verifier)
    logger.info(f"Verifier guardado para user_id: {user_id}, verifier: {verifier}")
    
    return {
        "auth_url": auth_url,
        "mensaje": "Redirige al usuario a esta URL"
    }


@router.get("/tiktok/callback")
async def callback_tiktok(
    code: str = Query(...), 
    state: str = Query(None)
):
    
    user_id = state or "default-user"
    
    logger.info("\n" + "="*80)
    logger.info("📥 TIKTOK CALLBACK RECIBIDO")
    logger.info("="*80)
    logger.info(f"👤 User ID (desde state): {user_id}")
    logger.info(f"🔑 Code recibido: {code[:20]}...")
    
    try:
        verifier_data = GestorTokens.obtener_verifier(user_id=user_id, red_social="tiktok")
        
        if not verifier_data:
            logger.error(f"❌ No se encontró verifier para user_id: {user_id}")
            raise Exception(
                f"Code Verifier no encontrado para user_id '{user_id}'. "
                f"Asegúrate de que el mismo user_id usado en /tiktok/conectar esté en el parámetro 'state'."
            )
        
        verifier = verifier_data['verifier']
        logger.info(f"✅ Verifier recuperado: {verifier[:20]}...")
        
        publicador = PublicadorTikTok()
        
        logger.info("🔄 Intercambiando código por token...")
        token_data = publicador.intercambiar_codigo_por_token(code, TIKTOK_REDIRECT_URI, verifier)
        
        # 🚨 SAFEGUARD: Check if token_data is a valid dictionary and has the access_token key.
        if not isinstance(token_data, dict) or not token_data.get("access_token"):
            logger.error(f"❌ Intercambio fallido. Respuesta de TikTok no válida: {token_data}")
            raise Exception("Intercambio de token fallido o access_token no recibido.")
            
        
        GestorTokens.eliminar_verifier(user_id=user_id, red_social="tiktok")
        
        GestorTokens.guardar_token(
            user_id=user_id,
            red_social="tiktok",
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data.get("expires_in"),
            metadata={"open_id": token_data.get("open_id")}
        )
        
        logger.info("="*80)
        logger.info("✅ TIKTOK CONECTADO EXITOSAMENTE")
        logger.info(f"👤 User ID: {user_id}")
        logger.info(f"🎯 Open ID: {token_data.get('open_id')}")
        logger.info(f"⏰ Expira en: {token_data.get('expires_in')} segundos")
        logger.info("="*80 + "\n")
        
        return {
            "success": True,
            "mensaje": "TikTok conectado exitosamente",
            "user_id": user_id,
            "open_id": token_data.get("open_id"),
            "expires_in": token_data.get("expires_in")
        }
        
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}")
        logger.error("="*80 + "\n")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/facebook/conectar")
async def conectar_facebook(user_id: str = Query(...)):
    
    publicador = PublicadorFacebook()
    
    auth_url = publicador.obtener_url_oauth(FACEBOOK_REDIRECT_URI)
    auth_url += f"&state={user_id}"
    
    logger.info("\n" + "="*80)
    logger.info("🔗 FACEBOOK - URL DE AUTENTICACIÓN GENERADA")
    logger.info("="*80)
    logger.info(f"👤 User ID: {user_id}")
    logger.info(f"\n📱 REDIRIGE AL USUARIO A ESTA URL:")
    logger.info(f"\n{auth_url}")
    logger.info(f"\n📥 Facebook redirigirá automáticamente a:")
    logger.info(f"{FACEBOOK_REDIRECT_URI}?code=XXX&state={user_id}")
    logger.info("="*80 + "\n")
    
    return {
        "auth_url": auth_url,
        "user_id": user_id,
        "redirect_uri": FACEBOOK_REDIRECT_URI,
        "mensaje": "Redirige al usuario a auth_url"
    }


@router.get("/facebook/callback")
async def callback_facebook(
    code: str = Query(...), 
    state: str = Query(None)
):
    
    user_id = state or "default-user"
    
    logger.info("\n" + "="*80)
    logger.info("📥 FACEBOOK CALLBACK RECIBIDO")
    logger.info("="*80)
    logger.info(f"👤 User ID (desde state): {user_id}")
    logger.info(f"🔑 Code recibido: {code[:20]}...")
    
    try:
        publicador = PublicadorFacebook()
        
        logger.info("🔄 Intercambiando código por token...")
        token_data = publicador.intercambiar_codigo_por_token(code, FACEBOOK_REDIRECT_URI)
        
        # 🚨 SAFEGUARD: Check if token_data is a valid dictionary and has the access_token key.
        if not isinstance(token_data, dict) or not token_data.get("access_token"):
            logger.error(f"❌ Intercambio fallido. Respuesta de Facebook no válida: {token_data}")
            raise Exception("Intercambio de token fallido o access_token no recibido.")
            
        GestorTokens.guardar_token(
            user_id=user_id,
            red_social="facebook",
            access_token=token_data["access_token"],
            expires_in=token_data.get("expires_in")
        )
        
        logger.info("="*80)
        logger.info("✅ FACEBOOK CONECTADO EXITOSAMENTE")
        logger.info(f"👤 User ID: {user_id}")
        logger.info(f"⏰ Expira en: {token_data.get('expires_in')} segundos")
        logger.info("="*80 + "\n")
        
        return {
            "success": True,
            "mensaje": "Facebook conectado exitosamente",
            "user_id": user_id,
            "expires_in": token_data.get("expires_in")
        }
        
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}")
        logger.error("="*80 + "\n")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tokens/{user_id}")
async def obtener_tokens_usuario(user_id: str):
    
    redes = ["tiktok", "facebook", "instagram", "linkedin"]
    tokens_activos = []
    
    for red in redes:
        if GestorTokens.usuario_tiene_token(user_id, red):
            tokens_activos.append(red)
    
    logger.info("\n" + "="*80)
    logger.info(f"📊 ESTADO DE TOKENS - User ID: {user_id}")
    logger.info("="*80)
    logger.info(f"✅ Redes conectadas: {', '.join(tokens_activos) if tokens_activos else 'Ninguna'}")
    logger.info("="*80 + "\n")
    
    return {
        "user_id": user_id,
        "redes_conectadas": tokens_activos
    }