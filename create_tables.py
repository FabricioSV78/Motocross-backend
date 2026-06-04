"""
Script para crear las tablas de la base de datos
Incluye la nueva tabla pilot_profiles (HU-05)
"""
from app.db.session import engine
from app.db.base import Base

print("*** Creando tablas en la base de datos...")
try:
    Base.metadata.create_all(bind=engine)
    print("[OK] Tablas creadas exitosamente!")
    print("\nTablas creadas:")
    print("  - users")
    print("  - pilot_profiles (nueva)")
    
    # Manual migration to add 'foto' column to 'coaches' table if it does not exist
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE coaches ADD COLUMN foto VARCHAR;"))
            conn.commit()
            print("  - Column 'foto' added to 'coaches' table successfully")
        except Exception as e:
            # Column might already exist, which is fine
            print(f"  - Column 'foto' migration note (may already exist): {e}")
except Exception as e:
    print(f"[ERROR] Error al crear tablas: {e}")
