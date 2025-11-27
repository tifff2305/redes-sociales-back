# app/utilidades/dependencias.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

# Importamos configuración y modelos
from app.config.bd import obtener_bd
from app.modelos.tablas import Usuario
from app.utilidades.seguridad import SECRET_KEY, ALGORITHM

# Esto le dice a Swagger que el login está en /auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def obtener_usuario_actual(token: str = Depends(oauth2_scheme), db: Session = Depends(obtener_bd)):
    """
    El 'Portero':
    1. Recibe el token.
    2. Lo decodifica.
    3. Busca al usuario en la BD.
    4. Si todo está bien, deja pasar y entrega el usuario.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificar el Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Buscar usuario en la Base de Datos PostgreSQL
    user = db.query(Usuario).filter(Usuario.email == email).first()
    
    if user is None:
        raise credentials_exception
        
    return user