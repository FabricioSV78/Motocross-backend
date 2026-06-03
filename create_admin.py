"""
Script para crear el usuario administrador por defecto.
Ejecutar UNA sola vez después de inicializar la base de datos.

Uso:
    cd motocross-backend
    .\venv\Scripts\Activate.ps1
    python create_admin.py

Credenciales del admin creado:
    Email:    admin@motocross.com
    Password: Admin1234!
"""
from app.db.session import SessionLocal
from app.db.base import Base  
from app.models.user import User
from app.models.enums import Role, Status
from app.core.security import get_password_hash

ADMIN_EMAIL = "admin@motocross.com"
ADMIN_PASSWORD = "Admin1234!"
ADMIN_NOMBRE = "Administrador"

print("=" * 50)
print("CREAR ADMIN POR DEFECTO")
print("=" * 50)

db = SessionLocal()
try:
    # Verificar si ya existe
    existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    if existing:
        # Si existe pero no es ADMIN, actualizarlo
        if existing.role != Role.ADMIN.value:
            existing.role = Role.ADMIN.value
            existing.status = Status.ACTIVE.value
            db.commit()
            print(f"✅ Usuario actualizado a ADMIN: {ADMIN_EMAIL}")
        else:
            print(f"⚠️  El admin ya existe: {ADMIN_EMAIL}")
    else:
        admin = User(
            email=ADMIN_EMAIL,
            nombre=ADMIN_NOMBRE,
            hashed_password=get_password_hash(ADMIN_PASSWORD),
            role=Role.ADMIN.value,
            status=Status.ACTIVE.value,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"✅ Admin creado correctamente (id={admin.id})")

    print()
    print("Credenciales:")
    print(f"  Email:    {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASSWORD}")
    print()
    print("Ahora puedes iniciar sesión en /login con estas credenciales.")
finally:
    db.close()
