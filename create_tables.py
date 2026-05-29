"""
Script para crear las tablas de la base de datos
Incluye la nueva tabla pilot_profiles (HU-05)
"""
from app.db.session import engine
from app.db.base import Base

print("✨ Creando tablas en la base de datos...")
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas exitosamente!")
    print("\nTablas creadas:")
    print("  - users")
    print("  - pilot_profiles (nueva)")
except Exception as e:
    print(f"❌ Error al crear tablas: {e}")
