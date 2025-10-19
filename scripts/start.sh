#!/bin/bash
set -e

echo "🚀 Iniciando aplicación ANB Rising Stars Showcase..."

# Función para esperar a que PostgreSQL esté disponible
wait_for_postgres() {
    echo "🔄 Esperando a que PostgreSQL esté disponible..."
    until python -c "import psycopg2; psycopg2.connect(host='postgres', port=5432, user='anb_user', password='anb_password', database='anb_db')" 2>/dev/null; do
        echo "⏳ PostgreSQL no está listo, esperando..."
        sleep 2
    done
    echo "✅ PostgreSQL está disponible"
}

# Función para limpiar base de datos si es necesario
clean_database_if_needed() {
    echo "🔍 Verificando estado de la base de datos..."
    
    # Verificar si existe la tabla alembic_version usando Python
    if ! python -c "
import psycopg2
try:
    conn = psycopg2.connect(host='postgres', port=5432, user='anb_user', password='anb_password', database='anb_db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM alembic_version LIMIT 1;')
    cursor.fetchone()
    cursor.close()
    conn.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; then
        echo "🧹 Base de datos no inicializada, limpiando..."
        python -c "
import psycopg2
conn = psycopg2.connect(host='postgres', port=5432, user='anb_user', password='anb_password', database='anb_db')
cursor = conn.cursor()
cursor.execute('DROP SCHEMA IF EXISTS public CASCADE;')
cursor.execute('CREATE SCHEMA public;')
conn.commit()
cursor.close()
conn.close()
"
        echo "✅ Base de datos limpiada"
    else
        echo "✅ Base de datos ya inicializada"
    fi
}

# Función para ejecutar migraciones
run_migrations() {
    echo "🚀 Ejecutando migraciones de Alembic..."
    
    # Ejecutar migraciones
    if alembic upgrade head; then
        echo "✅ Migraciones aplicadas correctamente"
    else
        echo "❌ Error aplicando migraciones"
        exit 1
    fi
}

# Función para iniciar la aplicación
start_application() {
    echo "🎯 Iniciando aplicación FastAPI..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
}

# Ejecutar secuencia de inicialización
main() {
    echo "🚀 Iniciando secuencia de inicialización..."
    
    # 1. Esperar a PostgreSQL
    wait_for_postgres
    
    # 2. Limpiar base de datos si es necesario
    clean_database_if_needed
    
    # 3. Ejecutar migraciones
    run_migrations
    
    # 4. Iniciar aplicación
    start_application
}

# Ejecutar función principal
main "$@"
