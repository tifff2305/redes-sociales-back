from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from app.config.bd import obtener_bd
from app.modelos.tablas import Chat, Mensaje, Usuario
from app.utilidades.dependencia import obtener_usuario_actual
from pydantic import BaseModel
import json

router = APIRouter(prefix="/historial", tags=["Historial"])

# Esquemas simples para responder
class ChatOut(BaseModel):
    id: int
    titulo: str
    fecha: str 

class MensajeOut(BaseModel):
    id: int
    rol: str
    contenido: str # Se enviará como string JSON
    fecha: str

# 1. OBTENER LISTA DE CHATS (Para la barra lateral)
@router.get("/chats", response_model=List[ChatOut])
def obtener_mis_chats(
    db: Session = Depends(obtener_bd),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    chats = db.query(Chat).filter(Chat.usuario_id == usuario.id).order_by(desc(Chat.fecha_creacion)).all()
    return [{"id": c.id, "titulo": c.titulo, "fecha": str(c.fecha_creacion)} for c in chats]

# 2. OBTENER MENSAJES DE UN CHAT ESPECÍFICO
@router.get("/chats/{chat_id}/mensajes", response_model=List[MensajeOut])
def obtener_mensajes(
    chat_id: int,
    db: Session = Depends(obtener_bd),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    # Verificamos que el chat sea del usuario
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.usuario_id == usuario.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    
    mensajes = db.query(Mensaje).filter(Mensaje.chat_id == chat_id).order_by(Mensaje.id.asc()).all()
    
    return [
        {
            "id": m.id, 
            "rol": m.rol, 
            # Si es assistant, ya está en JSON string por el Paso 0. Si es user, es texto plano.
            "contenido": m.contenido, 
            "fecha": str(m.fecha)
        } 
        for m in mensajes
    ]