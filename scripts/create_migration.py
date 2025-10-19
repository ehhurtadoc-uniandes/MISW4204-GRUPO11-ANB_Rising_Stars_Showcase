#!/usr/bin/env python3
"""
Script para crear migraciones de Alembic con IDs válidos.
Uso: python scripts/create_migration.py "descripción de la migración"
"""

import sys
import hashlib
import os
from datetime import datetime

def generate_migration_id(description):
    """Genera un ID válido para la migración basado en la descripción y timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    content = f"{description}_{timestamp}".encode('utf-8')
    return hashlib.md5(content).hexdigest()[:12]

def create_migration_file(description):
    """Crea un archivo de migración con ID válido."""
    migration_id = generate_migration_id(description)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    
    filename = f"alembic/versions/{migration_id}_{description.replace(' ', '_').lower()}.py"
    
    content = f'''"""Migration: {description}

Revision ID: {migration_id}
Revises: 
Create Date: {timestamp}

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '{migration_id}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add your migration logic here
    pass


def downgrade() -> None:
    # Add your rollback logic here
    pass
'''
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"✅ Migración creada: {filename}")
    print(f"📝 ID: {migration_id}")
    print(f"📄 Descripción: {description}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("❌ Uso: python scripts/create_migration.py 'descripción de la migración'")
        sys.exit(1)
    
    description = sys.argv[1]
    create_migration_file(description)
