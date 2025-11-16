# app/api/chat_routes.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import obtener_db
from app.core.models import Usuario, GeneracionContenido
from app.chat.chat_service import ChatService

# Crear el router
router = APIRouter(prefix="/chat", tags=["Chat"])

# Instancia del servicio de chat (en producción, una por usuario)
OPENAI_API_KEY = "tu-api-key-aqui"
chat_service = ChatService(api_key=OPENAI_API_KEY)


# Modelos de entrada/salida
class MensajeRequest(BaseModel):
    """Lo que el usuario envía"""
    usuario_id: str
    mensaje: str


class MensajeResponse(BaseModel):
    """Lo que la API responde"""
    exito: bool
    tipo: str
    respuesta: str = None
    contenido: dict = None
    error: str = None


@router.post("/mensaje", response_model=MensajeResponse)
def enviar_mensaje(request: MensajeRequest, db: Session = Depends(obtener_db)):
    """
    Endpoint principal del chat
    
    POST /chat/mensaje
    Body: {"usuario_id": "123", "mensaje": "Crea post para Facebook"}
    """
    
    # Verificar que el usuario existe
    usuario = db.query(Usuario).filter(Usuario.id == request.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Procesar mensaje
    resultado = chat_service.procesar_mensaje(request.mensaje)
    
    # Si generó contenido, guardar en BD
    if resultado.get("exito") and resultado.get("tipo") == "contenido":
        
        generacion = GeneracionContenido(
            usuario_id=request.usuario_id,
            nombre_tema=f"Contenido para {resultado['red_social']}",
            prompt=request.mensaje,
            modelo_ia="gpt-4",
            estado="GENERADO",
            resultados=[resultado["contenido"]]
        )
        db.add(generacion)
        db.commit()
        
        return MensajeResponse(
            exito=True,
            tipo="contenido",
            respuesta=f"Contenido generado para {resultado['red_social']}",
            contenido=resultado["contenido"]
        )
    
    # Si es conversación normal
    elif resultado.get("exito") and resultado.get("tipo") == "conversacion":
        return MensajeResponse(
            exito=True,
            tipo="conversacion",
            respuesta=resultado["respuesta"]
        )
    
    # Si hubo error
    else:
        return MensajeResponse(
            exito=False,
            tipo="error",
            error=resultado.get("error", "Error desconocido")
        )


@router.get("/generaciones/{usuario_id}")
def obtener_generaciones(usuario_id: str, db: Session = Depends(obtener_db)):
    """
    Obtiene las generaciones de contenido del usuario
    
    GET /chat/generaciones/123
    """
    generaciones = db.query(GeneracionContenido)\
        .filter(GeneracionContenido.usuario_id == usuario_id)\
        .order_by(GeneracionContenido.fecha.desc())\
        .limit(20)\
        .all()
    
    return {
        "total": len(generaciones),
        "generaciones": [
            {
                "id": g.id,
                "tema": g.nombre_tema,
                "fecha": g.fecha.isoformat(),
                "estado": g.estado,
                "resultados": g.resultados
            }
            for g in generaciones
        ]
    }


@router.post("/limpiar-historial")
def limpiar_historial():
    """
    Limpia el historial del chat
    
    POST /chat/limpiar-historial
    """
    chat_service.historial = []
    return {"mensaje": "Historial limpiado"}