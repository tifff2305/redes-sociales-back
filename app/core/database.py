# app/core/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Datos de tu PostgreSQL local
usuario = "postgres"
contraseña = "8942186"
base_datos = "red-social"

# Conectar a PostgreSQL
conexion = f"postgresql://{usuario}:{contraseña}@localhost:5432/{base_datos}"
engine = create_engine(conexion)

# Para crear sesiones de base de datos
Session = sessionmaker(bind=engine)

# Para definir tus tablas
Base = declarative_base()

def obtener_db():
    """Abre y cierra la base de datos automáticamente"""
    db = Session()
    try:
        yield db
    finally:
        db.close()