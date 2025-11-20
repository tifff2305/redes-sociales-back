"""from typing import Dict, Any
import logging
from app.core.servicios.NInteligencia_Artificial.tiktok import PublicadorTikTok
from app.core.servicios.NInteligencia_Artificial.facebook import PublicadorFacebook
from app.repositorios.tokens import GestorTokens

logger = logging.getLogger(__name__)


class ServicioOAuth:
    
    def __init__(self, tiktok_redirect_uri: str, facebook_redirect_uri: str):
        self.tiktok_redirect_uri = tiktok_redirect_uri
        self.facebook_redirect_uri = facebook_redirect_uri
    
    def iniciar_tiktok(self, user_id: str) -> Dict[str, Any]:
        publicador = PublicadorTikTok()
        auth_url, verifier = publicador.obtener_url_oauth_con_verifier(self.tiktok_redirect_uri, user_id)
        
        GestorTokens.guardar_verifier(user_id=user_id, red_social="tiktok", verifier=verifier)
        logger.info(f"Verifier guardado para user_id: {user_id}, verifier: {verifier}")
        
        return {
            "auth_url": auth_url,
            "mensaje": "Redirige al usuario a esta URL"
        }
    
    def callback_tiktok(self, code: str, state: str) -> Dict[str, Any]:
        user_id = state or "default-user"       
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
        token_data = publicador.intercambiar_codigo_por_token(code, self.tiktok_redirect_uri, verifier)
        
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
        
        return {
            "success": True,
            "mensaje": "TikTok conectado exitosamente",
            "user_id": user_id,
            "open_id": token_data.get("open_id"),
            "expires_in": token_data.get("expires_in")
        }
    
    def iniciar_facebook(self, user_id: str) -> Dict[str, Any]:
        publicador = PublicadorFacebook()
        
        auth_url = publicador.obtener_url_oauth(self.facebook_redirect_uri)
        auth_url += f"&state={user_id}"
        
        return {
            "auth_url": auth_url,
            "user_id": user_id,
            "redirect_uri": self.facebook_redirect_uri,
            "mensaje": "Redirige al usuario a auth_url"
        }
    
    def callback_facebook(self, code: str, state: str) -> Dict[str, Any]:
        user_id = state or "default-user"      
        publicador = PublicadorFacebook()
        
        logger.info("🔄 Intercambiando código por token...")
        token_data = publicador.intercambiar_codigo_por_token(code, self.facebook_redirect_uri)
        
        if not isinstance(token_data, dict) or not token_data.get("access_token"):
            logger.error(f"❌ Intercambio fallido. Respuesta de Facebook no válida: {token_data}")
            raise Exception("Intercambio de token fallido o access_token no recibido.")
        
        GestorTokens.guardar_token(
            user_id=user_id,
            red_social="facebook",
            access_token=token_data["access_token"],
            expires_in=token_data.get("expires_in")
        )

        return {
            "success": True,
            "mensaje": "Facebook conectado exitosamente",
            "user_id": user_id,
            "expires_in": token_data.get("expires_in")
        }
    
    def obtener_estado_tokens(self, user_id: str) -> Dict[str, Any]:
        redes = ["tiktok", "facebook", "instagram", "linkedin"]
        tokens_activos = []
        
        for red in redes:
            if GestorTokens.usuario_tiene_token(user_id, red):
                tokens_activos.append(red)
        
        return {
            "user_id": user_id,
            "redes_conectadas": tokens_activos
        }"""