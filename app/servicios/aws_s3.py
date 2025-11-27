import boto3
import os
import logging
from botocore.exceptions import NoCredentialsError
from app.config.configuracion import obtener_configuracion

logger = logging.getLogger(__name__)

class GestorS3:
    def __init__(self):
        config = obtener_configuracion()
        
        self.bucket_name = config.AWS_S3_BUCKET_NAME
        self.region = config.AWS_REGION
        
        # Conexión con AWS
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=self.region
        )

    def subir_archivo(self, ruta_archivo: str, nombre_destino: str) -> str:
        """
        Sube un archivo local a S3 y retorna su URL pública.
        """
        try:
            # 1. Detectar tipo de contenido (Para que el navegador sepa si es imagen o video)
            ext = nombre_destino.split('.')[-1].lower()
            content_type = "application/octet-stream"
            if ext in ['jpg', 'jpeg']: content_type = "image/jpeg"
            elif ext == 'png': content_type = "image/png"
            elif ext == 'mp4': content_type = "video/mp4"

            logger.info(f"☁️ Subiendo a S3: {nombre_destino}...")

            # 2. Subir archivo
            with open(ruta_archivo, "rb") as data:
                self.s3.upload_fileobj(
                    data, 
                    self.bucket_name, 
                    nombre_destino,
                    ExtraArgs={'ContentType': content_type} 
                    # Nota: Si tu bucket NO es público por política, 
                    # podrías necesitar agregar: 'ACL': 'public-read' aquí.
                )

            # 3. Construir URL Pública
            # Formato estándar: https://BUCKET.s3.REGION.amazonaws.com/ARCHIVO
            url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{nombre_destino}"
            
            logger.info(f"✅ Subida exitosa. URL: {url}")
            return url

        except FileNotFoundError:
            raise Exception("El archivo no se encontró para subir a S3")
        except NoCredentialsError:
            raise Exception("Credenciales de AWS incorrectas")
        except Exception as e:
            logger.error(f"❌ Error S3: {e}")
            raise Exception(f"Error subiendo a S3: {e}")