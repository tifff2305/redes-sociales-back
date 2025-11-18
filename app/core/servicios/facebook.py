import requests
from typing import Dict, Any
from app.core.servicios.base_publicar import PublicadorBase
import os

class PublicadorFacebook(PublicadorBase):
    
    def __init__(self):
        super().__init__("facebook")
        self.app_id = os.getenv("FACEBOOK_APP_ID")
        self.app_secret = os.getenv("FACEBOOK_APP_SECRET")
        self.graph_url = "https://graph.facebook.com/v18.0"
    
    def obtener_url_oauth(self, redirect_uri: str) -> str:
        
        scopes = "pages_manage_posts,pages_read_engagement"
        
        url = f"https://www.facebook.com/v18.0/dialog/oauth?"
        url += f"client_id={self.app_id}"
        url += f"&redirect_uri={redirect_uri}"
        url += f"&scope={scopes}"
        url += "&response_type=code"
        
        return url
    
    def intercambiar_codigo_por_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        
        url = f"{self.graph_url}/oauth/access_token"
        
        params = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "redirect_uri": redirect_uri,
            "code": code
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            raise Exception(f"Error obteniendo token: {response.text}")
        
        data = response.json()
        
        return {
            "access_token": data.get("access_token"),
            "token_type": data.get("token_type"),
            "expires_in": data.get("expires_in")
        }
    
    def publicar(self, contenido: Dict[str, Any], access_token: str, page_id: str = None) -> Dict[str, Any]:
        
        if not page_id:
            raise ValueError("Facebook requiere page_id para publicar")
        
        texto = contenido.get("text", "")
        
        url = f"{self.graph_url}/{page_id}/feed"
        
        payload = {
            "message": texto,
            "access_token": access_token
        }
        
        response = requests.post(url, data=payload)
        
        if response.status_code != 200:
            raise Exception(f"Error publicando en Facebook: {response.text}")
        
        data = response.json()
        
        return {
            "success": True,
            "post_id": data.get("id"),
            "message": "Publicado en Facebook exitosamente"
        }