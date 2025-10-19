#!/usr/bin/env python3
"""
Script de inicialización de base de datos que maneja migraciones automáticamente.
Se ejecuta automáticamente al iniciar el contenedor.
"""

import os
import sys
import subprocess
import time
import psycopg2
from psycopg2 import sql
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_postgres(max_retries=30, delay=2):
    """Espera a que PostgreSQL esté disponible."""
    logger.info("🔄 Esperando a que PostgreSQL esté disponible...")
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'postgres'),
                port=os.getenv('POSTGRES_PORT', '5432'),
                user=os.getenv('POSTGRES_USER', 'anb_user'),
                password=os.getenv('POSTGRES_PASSWORD', 'anb_password'),
                database=os.getenv('POSTGRES_DB', 'anb_db')
            )
            conn.close()
            logger.info("✅ PostgreSQL está disponible")
            return True
        except psycopg2.OperationalError as e:
            logger.info(f"⏳ Intento {attempt + 1}/{max_retries}: {e}")
            time.sleep(delay)
    
    logger.error("❌ No se pudo conectar a PostgreSQL después de todos los intentos")
    return False

def check_alembic_version():
    """Verifica si existe la tabla alembic_version."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'postgres'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            user=os.getenv('POSTGRES_USER', 'anb_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'anb_password'),
            database=os.getenv('POSTGRES_DB', 'anb_db')
        )
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'alembic_version'
            );
        """)
        
        exists = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return exists
    except Exception as e:
        logger.error(f"❌ Error verificando alembic_version: {e}")
        return False

def clean_database():
    """Limpia la base de datos completamente."""
    logger.info("🧹 Limpiando base de datos...")
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'postgres'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            user=os.getenv('POSTGRES_USER', 'anb_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'anb_password'),
            database=os.getenv('POSTGRES_DB', 'anb_db')
        )
        
        cursor = conn.cursor()
        cursor.execute("DROP SCHEMA IF EXISTS public CASCADE;")
        cursor.execute("CREATE SCHEMA public;")
        conn.commit()
        
        cursor.close()
        conn.close()
        
        logger.info("✅ Base de datos limpiada")
        return True
    except Exception as e:
        logger.error(f"❌ Error limpiando base de datos: {e}")
        return False

def run_alembic_upgrade():
    """Ejecuta alembic upgrade."""
    logger.info("🚀 Ejecutando migraciones de Alembic...")
    
    try:
        result = subprocess.run(
            ['alembic', 'upgrade', 'head'],
            capture_output=True,
            text=True,
            cwd='/app'
        )
        
        if result.returncode == 0:
            logger.info("✅ Migraciones aplicadas correctamente")
            return True
        else:
            logger.error(f"❌ Error en migraciones: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Error ejecutando alembic: {e}")
        return False

def main():
    """Función principal de inicialización."""
    logger.info("🚀 Iniciando inicialización de base de datos...")
    
    # 1. Esperar a que PostgreSQL esté disponible
    if not wait_for_postgres():
        sys.exit(1)
    
    # 2. Verificar si ya existe alembic_version
    if check_alembic_version():
        logger.info("✅ Base de datos ya inicializada")
        return
    
    # 3. Limpiar base de datos si es necesario
    if not clean_database():
        sys.exit(1)
    
    # 4. Ejecutar migraciones
    if not run_alembic_upgrade():
        sys.exit(1)
    
    logger.info("🎉 Inicialización completada exitosamente")

if __name__ == "__main__":
    main()
