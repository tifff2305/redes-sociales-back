# app/bd.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# TUS DATOS:
# User: postgres
# Pass: 8942186
# Host: localhost
# Port: 5432
# DB:   Redes_Sociales

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:8942186@localhost:5432/Redes_Sociales"

# 1. Crear el Motor (Engine)
# Conecta Python con PostgreSQL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 2. Crear el generador de Sesiones
# Cada vez que un usuario haga una petición, abriremos una 'SessionLocal'
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. La Base para tus Modelos (Tablas)
# Esto lo usan tus archivos en 'app/modelos/' para saber que son tablas SQL
Base = declarative_base()

# 4. Dependencia (Dependency Injection)
# Esta función se usa en los endpoints (rutas) para abrir y cerrar la conexión automáticamente
def obtener_bd():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()