import os
from fastapi import FastAPI, HTTPException, File, UploadFile, Form 
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
from app.core.prompt import obtener_prompt
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Generador Contenido", version="1.0.0")
app.include_router(oauth_router)

# ⭐ CACHE PARA ALMACENAR EL ÚLTIMO CONTENIDO GENERADO POR USUARIO
contenido_cache: Dict[str, Dict[str, Any]] = {}

try:
    openai_client = OpenAI()
    generador = GeneradorContenido(
        openai_client=openai_client,
        modelo_db=GeneracionContenido,
        modelo_ia="gpt-4o-mini"
    )
    logger.info("✅ Generador inicializado")
except Exception as e:
    logger.error(f"❌ Error: {e}")
    generador = None


class SolicitudContenido(BaseModel):
    contenido: str = Field(..., min_length=10)
    target_networks: List[str]
    user_id: str = "api-user"  # ⭐ Default = "api-user" para coincidir con tu setup
    
    class Config:
        json_schema_extra = {
            "example": {
                "contenido": "Lanzamos una característica para gestionar trámites",
                "target_networks": ["tiktok", "facebook"],
                "user_id": "usuario123"
            }
        }


@app.get("/")
async def root():
    return {
        "mensaje": "API Generador de Contenido Multi-Plataforma",
        "version": "1.0.0",
        "endpoints": {
            "generar": "/generar-contenido",
            "conectar_tiktok": "/tiktok/conectar?user_id=YOUR_USER_ID",
            "conectar_facebook": "/facebook/conectar?user_id=YOUR_USER_ID",
            "publicar": "POST /publicar (con archivo, sin texto manual)",
            "tokens": "/tokens/{user_id}",
            "docs": "/docs"
        }
    }


@app.post("/generar-contenido", response_model=Dict[str, Any])
async def generar_contenido(request: SolicitudContenido):
    """
    Genera contenido optimizado para redes sociales.
    El contenido se guarda automáticamente en caché por user_id.
    """
    try:
        contenido = obtener_prompt()
        
        resultado = generador.generar_y_guardar_contenido(
            user_id=request.user_id,
            contenido=contenido,
            target_networks=request.target_networks
        )
        
        if not resultado:
            raise HTTPException(status_code=500, detail="Error interno: No se generó contenido")
        
        # ⭐ GUARDAR EN CACHE por user_id
        contenido_cache[request.user_id] = resultado
        
        logger.info(f"✅ Contenido generado y guardado en caché para user_id: {request.user_id}")
        logger.info(f"   Redes: {', '.join(request.target_networks)}")
        
        # Devuelve el contenido generado por red social
        response_data = {}
        
        for red in request.target_networks:
            if red in resultado:
                response_data[red] = {
                    "text": resultado[red].get("text"),
                    "hashtags": resultado[red].get("hashtags"),
                    "character_count": resultado[red].get("character_count"),
                }
                
                if red == "tiktok" and "video_hook" in resultado[red]:
                    response_data[red]["video_hook"] = resultado[red]["video_hook"]
                
                if red == "instagram" and "suggested_image_prompt" in resultado[red]:
                    response_data[red]["suggested_image_prompt"] = resultado[red]["suggested_image_prompt"]
        
        return response_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@app.post("/publicar", response_model=Dict[str, Any])
async def publicar_contenido(
    user_id: str = Form(...),
    red_social: str = Form(...),
    video_file: UploadFile = File(...),
    texto: Optional[str] = Form(None),  # ⭐ Ahora es OPCIONAL
):
    """
    Publica contenido en redes sociales.
    
    ✨ NUEVO COMPORTAMIENTO:
    - Si NO envías 'texto', usa automáticamente el último generado para este user_id y red_social
    - Si SÍ envías 'texto', usa ese texto personalizado
    
    Flujo recomendado:
    1. POST /generar-contenido con user_id y target_networks
    2. POST /publicar con user_id y red_social (SIN texto)
    3. El sistema usa automáticamente el texto generado en paso 1
    """
    try:
        video_content = await video_file.read()
        video_size = len(video_content)
        video_filename = video_file.filename
        video_mime_type = video_file.content_type

        if video_mime_type != "video/mp4":
            raise HTTPException(status_code=400, detail="Solo se permiten archivos de video MP4")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo subido: {str(e)}")

    print("\n" + "="*80)
    print("📥 RECEPCIÓN DE SOLICITUD DE PUBLICACIÓN")
    print("="*80)
    print(f"👤 User ID: {user_id}")
    print(f"🌐 Red Social: {red_social}")
    print(f"📹 Archivo: {video_filename} ({video_size} bytes)")
    print(f"📝 Texto manual enviado: {'Sí' if texto else 'No (usará caché)'}")

    # ⭐ SI NO SE ENVIÓ TEXTO, BUSCAR EN CACHÉ
    if not texto:
        print("\n🔍 Buscando texto en caché...")
        
        if user_id not in contenido_cache:
            print(f"❌ No hay contenido generado para user_id: {user_id}")
            print("="*80 + "\n")
            raise HTTPException(
                status_code=400,
                detail=f"Debes generar contenido primero usando /generar-contenido con user_id={user_id}"
            )
        
        contenido_usuario = contenido_cache[user_id]
        
        if red_social not in contenido_usuario:
            redes_disponibles = list(contenido_usuario.keys())
            print(f"❌ No hay contenido generado para {red_social}")
            print(f"   Redes disponibles: {', '.join(redes_disponibles)}")
            print("="*80 + "\n")
            raise HTTPException(
                status_code=400,
                detail=f"No hay contenido generado para {red_social}. Redes disponibles: {redes_disponibles}"
            )
        
        # ⭐ OBTENER EL TEXTO DEL CACHÉ
        texto = contenido_usuario[red_social].get("text")
        print(f"✅ Texto recuperado del caché:")
        print(f"   Primeros 100 caracteres: {texto[:100]}...")
    else:
        print(f"✅ Usando texto personalizado enviado")

    # Verificar token
    if not GestorTokens.usuario_tiene_token(user_id, red_social):
        print(f"❌ Usuario no tiene token para {red_social}")
        print("="*80 + "\n")
        raise HTTPException(
            status_code=401,
            detail=f"Usuario no tiene token para {red_social}. Debe conectar su cuenta primero"
        )

    token_data = GestorTokens.obtener_token(user_id, red_social)
    access_token = token_data["access_token"]
    print(f"🔑 Token encontrado: {access_token[:20]}...")

    # Preparar contenido para publicar
    contenido = {
        "text": texto,
        "video_file": video_file,
        "video_size": video_size,
        "privacy_level": "SELF_ONLY"
    }

    try:
        if red_social == "tiktok":
            publicador = PublicadorTikTok()
            print("📲 Publicando en TikTok...")
            resultado = publicador.publicar(contenido, access_token) 

        elif red_social == "facebook":
            page_id = token_data.get("metadata", {}).get("page_id")
            if not page_id:
                raise HTTPException(status_code=400, detail="Facebook requiere page_id")
            publicador = PublicadorFacebook()
            print("📲 Publicando en Facebook...")
            resultado = {"message": "Facebook en desarrollo"}

        else:
            raise HTTPException(status_code=400, detail=f"Red social {red_social} no soportada aún")

        print("="*80)
        print("✅ PUBLICACIÓN EXITOSA")
        print(f"🎯 {red_social.upper()}")
        print(f"🆔 ID Publicación: {resultado.get('post_id') or resultado.get('publish_id')}")
        print("="*80 + "\n")

        return resultado

    except Exception as e:
        print(f"❌ ERROR AL PUBLICAR: {str(e)}")
        print("="*80 + "\n")
        logger.error(f"Error publicando: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cache/{user_id}")
async def ver_cache_usuario(user_id: str):
    """
    Endpoint para ver qué contenido tiene guardado un usuario en caché.
    Útil para debugging.
    """
    if user_id not in contenido_cache:
        return {
            "user_id": user_id,
            "contenido": None,
            "mensaje": "No hay contenido en caché para este usuario"
        }
    
    contenido = contenido_cache[user_id]
    return {
        "user_id": user_id,
        "redes_disponibles": list(contenido.keys()),
        "contenido": contenido
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)