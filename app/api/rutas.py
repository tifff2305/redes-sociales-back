import os
from fastapi import FastAPI, HTTPException, File, UploadFile, Form # <- AGREGAR File, UploadFile, Form
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from openai import OpenAI
from google import genai 
from app.core.generador_contenido import GeneradorContenido
from app.db.modelos import GeneracionContenido
from app.db.tokens import GestorTokens
from app.core.servicios.tiktok import PublicadorTikTok
from app.core.servicios.facebook import PublicadorFacebook
from app.api.rutas_oauth import router as oauth_router
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Generador Contenido", version="1.0.0")
app.include_router(oauth_router)

try:
    openai_client = OpenAI()
    generador = GeneradorContenido(
        openai_client=openai_client,
        modelo_db=GeneracionContenido,
        modelo_ia="gpt-4o-mini"
    )
    logger.info(" Generador inicializado")
except Exception as e:
    logger.error(f" Error: {e}")
    generador = None


class SolicitudContenido(BaseModel):
    contenido: str = Field(..., min_length=10)
    target_networks: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "contenido": "Lanzamos una característica para gestionar trámites",
                "target_networks": ["facebook", "instagram", "linkedin"]
            }
        }

class PublicarRequest(BaseModel):
    user_id: str
    red_social: str
    texto: str
    video_file: str  # Ruta del archivo

# NOTA: SolicitudPublicar ha sido eliminada y su lógica se ha movido a @app.post("/publicar")

@app.get("/")
async def root():
    # ... (código sin cambios) ...
    return {
        "mensaje": "API Generador de Contenido Multi-Plataforma",
        "version": "1.0.0",
        "endpoints": {
            "generar": "/generar-contenido",
            "conectar_tiktok": "/tiktok/conectar?user_id=YOUR_USER_ID",
            "conectar_facebook": "/facebook/conectar?user_id=YOUR_USER_ID",
            "publicar": "POST /publicar (con archivo)",
            "tokens": "/tokens/{user_id}",
            "docs": "/docs"
        }
    }


@app.post("/generar-contenido", response_model=Dict[str, Any])
async def generar_contenido(request: SolicitudContenido):
    try:
        resultado = generador.generar_y_guardar_contenido(
            user_id="api-user",
            contenido=request.contenido,
            target_networks=request.target_networks
        )
        if not resultado:
            raise HTTPException(status_code=500, detail="Error interno: No se generó contenido")
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.post("/publicar", response_model=Dict[str, Any])
async def publicar_contenido(
    user_id: str = Form(...),
    red_social: str = Form(...),
    texto: Optional[str] = Form(None),
    page_id: Optional[str] = Form(None),
    video_file: UploadFile = File(...),
):
    try:
        video_content = await video_file.read()
        video_size = len(video_content)
        video_filename = video_file.filename
        video_mime_type = video_file.content_type

        if video_mime_type != "video/mp4":
            raise HTTPException(status_code=400, detail="Solo se permiten archivos de video MP4")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo subido: {str(e)}")
    # --- FIN PROCESAMIENTO DE ARCHIVO ---

    # Log para verificar recepción de archivo
    if not video_file:
        raise HTTPException(status_code=422, detail="Archivo 'video_file' no recibido")

    print("\n" + "="*80)
    print(" RECEPCIÓN DE ARCHIVO")
    print("="*80)
    print(f" Nombre del archivo: {video_file.filename}")
    print(f" Tipo MIME: {video_file.content_type}")
    print("="*80 + "\n")

    print("\n" + "="*80)
    print(" SOLICITUD DE PUBLICACIÓN DE ARCHIVO (FORM-DATA)")
    print("="*80)
    print(f" User ID: {user_id}")
    print(f" Red Social: {red_social}")
    print(f" Archivo subido: {video_filename} ({video_size} bytes)") # <- LOG SIZE

    if not GestorTokens.usuario_tiene_token(user_id, red_social):
        print(f" Usuario no tiene token para {red_social}")
        print("="*80 + "\n")
        raise HTTPException(
            status_code=401,
            detail=f"Usuario no tiene token para {red_social}. Debe conectar su cuenta primero en /tiktok/conectar?user_id={user_id}"
        )

    token_data = GestorTokens.obtener_token(user_id, red_social)
    access_token = token_data["access_token"]
    print(f" Token encontrado: {access_token[:20]}...")

    # Prepara el contenido para el publicador
    contenido = {
        "text": texto or f"Publicación automática de video: {video_filename}",
        "video_file": video_file, # Pasamos el objeto UploadFile directamente
        "video_size": video_size ,
        "privacy_level": "SELF_ONLY"
    }

    try:
        if red_social == "tiktok":
            publicador = PublicadorTikTok()
            print(" Publicando en TikTok...")
            resultado = publicador.publicar(contenido, access_token) 

        elif red_social == "facebook":
            if not page_id:
                raise HTTPException(status_code=400, detail="Facebook requiere page_id")
            publicador = PublicadorFacebook()
            print(" Publicando en Facebook...")
            # El publicador de FB también debe adaptarse para recibir el objeto UploadFile
            # resultado = publicador.publicar(contenido, access_token, page_id) # Descomentar cuando se implemente
            resultado = {"message": "Facebook en desarrollo"} # Placeholder

        else:
            raise HTTPException(status_code=400, detail=f"Red social {red_social} no soportada aún")

        print("="*80)
        print(" PUBLICACIÓN EXITOSA")
        print(f"📱 {red_social.upper()}")
        print(f" ID Publicación: {resultado.get('post_id') or resultado.get('publish_id')}")
        print("="*80 + "\n")

        return resultado

    except Exception as e:
        print(f" ERROR AL PUBLICAR: {str(e)}")
        print("="*80 + "\n")
        logger.error(f"Error publicando: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
