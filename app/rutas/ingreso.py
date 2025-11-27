# app/rutas/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Importamos tus herramientas
from app.config.bd import obtener_bd
from app.modelos.tablas import Usuario  # Tu modelo SQL
from app.modelos.esquemas import UsuarioRegistro, UsuarioLogin, TokenResponse # Tus modelos JSON
from app.utilidades.seguridad import encriptar_password, verificar_password, crear_token_acceso

# Creamos el router separado
router = APIRouter(prefix="", tags=["Autenticación"])

# ==========================================
# 1. ENDPOINT: REGISTRO
# ==========================================
@router.post("/registro", status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario: UsuarioRegistro, db: Session = Depends(obtener_bd)):
    
    # 1. Verificar si el email ya existe
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="El correo electrónico ya está registrado"
        )

    # 2. Crear el nuevo usuario (Hasheando la contraseña)
    nuevo_usuario = Usuario(
        nombre=usuario.nombre,
        email=usuario.email,
        contrasena_hash=encriptar_password(usuario.password) # <--- Importante: Hashear aquí
    )

    # 3. Guardar en BD
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return {"mensaje": "Usuario creado exitosamente", "id": nuevo_usuario.id}


# ==========================================
# 2. ENDPOINT: LOGIN
# ==========================================
@router.post("/login", response_model=TokenResponse)
def login_usuario(credenciales: UsuarioLogin, db: Session = Depends(obtener_bd)):
    
    # 1. Buscar usuario por email
    usuario_db = db.query(Usuario).filter(Usuario.email == credenciales.email).first()

    # 2. Validar que exista y que la contraseña coincida
    if not usuario_db:
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")
        
    if not verificar_password(credenciales.password, usuario_db.contrasena_hash):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    # 3. Generar el Token JWT
    access_token = crear_token_acceso(data={"sub": usuario_db.email})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": usuario_db.nombre
    }