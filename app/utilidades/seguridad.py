# app/utilidades/seguridad.py
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
import os
from typing import Union

# Configuración
SECRET_KEY = os.getenv("SECRET_KEY", "clave_super_secreta_indescifrable_123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 

# --- CAMBIO CLAVE AQUÍ ---
# Cambiamos "bcrypt" por "argon2" para evitar el error de los 72 bytes
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# ... (El resto de funciones sigue IGUAL) ...

def encriptar_password(password: str) -> str:
    return pwd_context.hash(password)

def verificar_password(password_plana: str, password_hasheada: str) -> bool:
    return pwd_context.verify(password_plana, password_hasheada)

def crear_token_acceso(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt