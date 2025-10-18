# 🚀 Mejores Prácticas para Migraciones de Alembic

## ❌ Problema Común

**Error:** `Can't locate revision identified by '001_initial_tables'`

**Causa:** IDs de migración inválidos que no siguen el formato esperado por Alembic.

## ✅ Solución

### 1. **IDs de Migración Válidos**

Alembic requiere IDs en formato hexadecimal de 12 caracteres:

```python
# ❌ INCORRECTO
revision = '001_initial_tables'
revision = 'a1b2c3d4e5f6'  # Muy corto
revision = 'initial_migration'

# ✅ CORRECTO
revision = '28074d007126'  # 12 caracteres hexadecimales
revision = 'a1b2c3d4e5f678'  # 12+ caracteres hexadecimales
```

### 2. **Generar IDs Válidos**

```bash
# Método 1: Usar el script automático
python scripts/create_migration.py "descripción de la migración"

# Método 2: Generar manualmente
python -c "import hashlib; print(hashlib.md5(b'initial_migration').hexdigest()[:12])"
```

### 3. **Estructura Correcta de Migración**

```python
"""Migration: Initial migration

Revision ID: 28074d007126
Revises: 
Create Date: 2024-10-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '28074d007126'  # ✅ ID válido
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Tu lógica de migración aquí
    pass

def downgrade() -> None:
    # Tu lógica de rollback aquí
    pass
```

## 🔧 Prevención de Problemas

### 1. **Script de Creación Automática**

Usa el script `scripts/create_migration.py` para crear migraciones:

```bash
python scripts/create_migration.py "Add user preferences table"
python scripts/create_migration.py "Update video status enum"
```

### 2. **Verificación Previa**

Antes de hacer commit, verifica que la migración sea válida:

```bash
# Verificar sintaxis
python -c "import alembic; print('✅ Alembic disponible')"

# Verificar estructura
alembic check
```

### 3. **Limpieza de Base de Datos**

Si hay problemas con migraciones existentes:

```bash
# Limpiar base de datos completamente
docker-compose exec postgres psql -U anb_user -d anb_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Reiniciar aplicación
docker-compose restart api
```

## 📋 Checklist de Migraciones

- [ ] ✅ ID de revisión en formato hexadecimal (12+ caracteres)
- [ ] ✅ Nombre de archivo descriptivo
- [ ] ✅ Funciones `upgrade()` y `downgrade()` implementadas
- [ ] ✅ Imports correctos (`alembic`, `sqlalchemy`)
- [ ] ✅ Pruebas en entorno de desarrollo
- [ ] ✅ Backup de base de datos antes de aplicar en producción

## 🚨 Solución de Problemas

### Error: "Can't locate revision"

1. **Verificar ID de migración:**
   ```bash
   grep -r "revision =" alembic/versions/
   ```

2. **Limpiar base de datos:**
   ```bash
   docker-compose exec postgres psql -U anb_user -d anb_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
   ```

3. **Recrear migración:**
   ```bash
   python scripts/create_migration.py "descripción"
   ```

### Error: "Revision already exists"

1. **Verificar migraciones existentes:**
   ```bash
   ls alembic/versions/
   ```

2. **Eliminar migración duplicada:**
   ```bash
   rm alembic/versions/migracion_duplicada.py
   ```

## 🎯 Mejores Prácticas

1. **Nunca editar migraciones aplicadas** - Crear nuevas migraciones
2. **Usar nombres descriptivos** - `add_user_preferences_table.py`
3. **Probar en desarrollo** - Antes de aplicar en producción
4. **Backup antes de migrar** - En entornos de producción
5. **Documentar cambios** - En el mensaje de commit

---

**💡 Tip:** Usa el script `scripts/create_migration.py` para evitar problemas con IDs de migración.
