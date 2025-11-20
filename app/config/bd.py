# Hardcoded database connection for development purposes

def obtener_db():
    """
    Simula una conexión a la base de datos devolviendo datos hardcodeados.
    """
    return {
        "usuarios": [
            {"id": 1, "nombre": "Usuario 1", "email": "usuario1@example.com"},
            {"id": 2, "nombre": "Usuario 2", "email": "usuario2@example.com"}
        ],
        "tokens": [
            {"id": 1, "usuario_id": 1, "token": "abc123"},
            {"id": 2, "usuario_id": 2, "token": "def456"}
        ]
    }