# app/modelos/tablas.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.config.bd import Base

# ==========================================
# 1. USUARIOS (Tabla Principal)
# ==========================================
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    contrasena_hash = Column(String(255), nullable=False)
    fecha_registro = Column(DateTime, default=datetime.now)

    # Relaciones: Un usuario tiene muchos tokens y muchos chats
    tokens = relationship("TokenRedSocial", back_populates="usuario", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="usuario", cascade="all, delete-orphan")


# ==========================================
# 2. TOKENS (Para no pedir login a cada rato)
# ==========================================
class TokenRedSocial(Base):
    __tablename__ = "tokens_redes"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    
    # "tiktok", "facebook", "instagram", "linkedin", "whatsapp"
    red_social = Column(String(50), nullable=False) 
    
    token_acceso = Column(Text, nullable=False)
    token_refresh = Column(Text, nullable=True)
    fecha_expiracion = Column(DateTime, nullable=True)

    usuario = relationship("Usuario", back_populates="tokens")


# ==========================================
# 3. CHATS (La carpeta de la conversación)
# ==========================================
class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    
    titulo = Column(String(150), default="Nuevo Chat") 
    fecha_creacion = Column(DateTime, default=datetime.now)
    
    # Relación: Un chat tiene muchos mensajes
    usuario = relationship("Usuario", back_populates="chats")
    mensajes = relationship("Mensaje", back_populates="chat", cascade="all, delete-orphan")


# ==========================================
# 4. MENSAJES (El historial real tipo ChatGPT)
# ==========================================
class Mensaje(Base):
    __tablename__ = "mensajes"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    
    # 'user' (lo que escribiste tú) o 'assistant' (lo que respondió la IA)
    rol = Column(String(20), nullable=False) 
    
    contenido = Column(Text, nullable=False) # El texto largo
    
    # Metadatos opcionales
    redes_objetivo = Column(String(200), nullable=True) # "tiktok, facebook"
    archivos_url = Column(Text, nullable=True) # Si generó imagen, guardamos la ruta
    
    fecha = Column(DateTime, default=datetime.now)

    chat = relationship("Chat", back_populates="mensajes")