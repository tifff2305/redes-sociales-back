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
    FACEBOOK_PAGE_ID: str = os.getenv("FACEBOOK_PAGE_ID")
    FACEBOOK_PAGE_ACCESS_TOKEN: str = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    
    # Instagram (usa mismas credenciales de Facebook)
    INSTAGRAM_APP_ID: str = os.getenv("INSTAGRAM_APP_ID")
    INSTAGRAM_PAGE_ACCESS_TOKEN: str = os.getenv("INSTAGRAM_PAGE_ACCESS_TOKEN")

    # LinkedIn
    ZAPIER_LINKEDIN_WEBHOOK: str = os.getenv("ZAPIER_LINKEDIN_WEBHOOK")
    IMGBB_API_KEY: str = os.getenv("IMGBB_API_KEY")

    # WhatsApp
    WHAPI_TOKEN: str = os.getenv("WHAPI_TOKEN")

    #AWS S3
    AWS_REGION: str = os.getenv("AWS_REGION")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET_NAME: str = os.getenv("AWS_S3_BUCKET_NAME")
    
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