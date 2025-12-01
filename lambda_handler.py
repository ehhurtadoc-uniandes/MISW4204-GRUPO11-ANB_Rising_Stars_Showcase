"""
Lambda handler para FastAPI
Usa Mangum como adaptador ASGI para ejecutar FastAPI en AWS Lambda
"""
from mangum import Mangum
from app.main import app

# Crear handler Lambda
# lifespan="off" porque Lambda no soporta lifespan events de FastAPI
handler = Mangum(app, lifespan="off")

