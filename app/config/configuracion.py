import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Configuracion:
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    MODELO_TEXTO: str = os.getenv("MODELO_TEXTO", "gpt-4o-mini")
    MODELO_IMAGEN: str = os.getenv("MODELO_IMAGEN", "gpt-image-1")
    MODELO_VIDEO: str = os.getenv("MODELO_VIDEO", "sora-2")
    
    # Base de datos
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./contenido.db")
    
    # TikTok
    TIKTOK_CLIENT_KEY: str = os.getenv("TIKTOK_CLIENT_KEY")
    TIKTOK_CLIENT_SECRET: str = os.getenv("TIKTOK_CLIENT_SECRET")
    TIKTOK_REDIRECT_URI: str = os.getenv("TIKTOK_REDIRECT_URI")
    
    # Facebook
    FACEBOOK_APP_ID: str = os.getenv("FACEBOOK_APP_ID")
    FACEBOOK_APP_SECRET: str = os.getenv("FACEBOOK_APP_SECRET")
    FACEBOOK_REDIRECT_URI: str = os.getenv("FACEBOOK_REDIRECT_URI")
    
    # Instagram (usa mismas credenciales de Facebook)
    INSTAGRAM_APP_ID: str = os.getenv("INSTAGRAM_APP_ID", os.getenv("FACEBOOK_APP_ID"))
    INSTAGRAM_APP_SECRET: str = os.getenv("INSTAGRAM_APP_SECRET", os.getenv("FACEBOOK_APP_SECRET"))
    
    def validar(self):
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY no configurada")
        if not self.TIKTOK_CLIENT_KEY:
            raise ValueError("TIKTOK_CLIENT_KEY no configurada")


@lru_cache()
def obtener_configuracion() -> Configuracion:
    config = Configuracion()
    config.validar()
    return config