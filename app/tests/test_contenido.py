# Ubicación: app/tests/test_contenido.py
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch
import io
import sys
import os

# --- AJUSTE DE IMPORTACIÓN ---
# Esto ayuda a Python a encontrar tu archivo 'contenido.py'
# sin importar si está en la raíz o en app/rutas.
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    # Intento 1: Lo correcto (dentro de rutas)
    from app.rutas.contenido import router
except ImportError:
    try:
        # Intento 2: Si está suelto en la raíz
        from contenido import router
    except ImportError:
        # Intento 3: Si el nombre del archivo es diferente, ajústalo aquí
        raise ImportError("❌ No encuentro 'contenido.py'. Asegúrate de que el archivo existe en 'app/rutas/' o en la raíz.")

# Creamos una app falsa solo para el test
app = FastAPI()
app.include_router(router)

client = TestClient(app)

# ==========================================
# TEST 1: Generar Contenido (Mock IA)
# ==========================================
@patch("app.servicios.ia.ServicioIA.generar_contenido_completo")
def test_generar_contenido_exitoso(mock_ia):
    mock_ia.return_value = {
        "whatsapp": {
            "text": "Texto generado", 
            "hashtags": ["#test"], 
            "image_path": "ruta/falsa.jpg"
        }
    }

    response = client.post("/generar", json={
        "contenido": "Vender zapatos",
        "redes": ["whatsapp"]
    })

    assert response.status_code == 200
    assert "whatsapp" in response.json()

# ==========================================
# TEST 2: Publicar WhatsApp (Mock Whapi)
# ==========================================
@patch("app.plataformas.whatsapp.WhatsApp.publicar_estado")
def test_publicar_whatsapp_ok(mock_whapi):
    mock_whapi.return_value = {"messages": [{"id": "MSG-TEST"}]}
    
    # Archivo falso en memoria
    archivo = io.BytesIO(b"imagen_falsa")
    archivo.name = "foto.jpg"

    response = client.post(
        "/publicar",
        data={"red_social": "whatsapp", "text": "Hola"},
        files={"archivo": ("foto.jpg", archivo, "image/jpeg")}
    )

    assert response.status_code == 200
    assert response.json()["detalles"]["whatsapp"]["status"] == "ok"

# ==========================================
# TEST 3: Publicar TikTok (Fallo Token)
# ==========================================
@patch("app.repositorios.tokens.GestorTokens.usuario_tiene_token")
def test_publicar_tiktok_sin_token(mock_token):
    mock_token.return_value = False
    archivo = io.BytesIO(b"video")
    
    response = client.post(
        "/publicar",
        data={"red_social": "tiktok", "text": "baila"},
        files={"archivo": ("video.mp4", archivo, "video/mp4")}
    )

    assert response.json()["detalles"]["tiktok"]["status"] == "error"

# ==========================================
# TEST 4: Publicar TikTok (Éxito)
# ==========================================
@patch("app.plataformas.tiktok.TikTok.publicar_video")
@patch("app.repositorios.tokens.GestorTokens.obtener_token")
@patch("app.repositorios.tokens.GestorTokens.usuario_tiene_token")
def test_publicar_tiktok_ok(mock_tiene, mock_get, mock_pub):
    mock_tiene.return_value = True
    mock_get.return_value = {"access_token": "abc"}
    mock_pub.return_value = {"id": "123"}
    
    archivo = io.BytesIO(b"video")
    response = client.post(
        "/publicar",
        data={"red_social": "tiktok", "text": "baila"},
        files={"archivo": ("video.mp4", archivo, "video/mp4")}
    )
    
    assert response.json()["detalles"]["tiktok"]["status"] == "ok"

# ==========================================
# TEST 5: Error Interno (CORREGIDO)
# ==========================================
@patch("app.servicios.ia.ServicioIA.generar_contenido_completo")
def test_error_interno(mock_ia):
    # Simulamos que la IA se rompe
    mock_ia.side_effect = Exception("Crash")
    
    # CAMBIO: Enviamos un texto > 10 caracteres para pasar la validación inicial
    payload = {
        "contenido": "Este es un texto de prueba valido para pasar la validacion", 
        "redes": ["whatsapp"]
    }
    
    response = client.post("/generar", json=payload)
    
    # Ahora sí debería dar 500 porque pasó la validación y chocó con el error simulado
    assert response.status_code == 500
    assert "Error interno IA" in response.json()["detail"]