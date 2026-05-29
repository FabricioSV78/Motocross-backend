"""
Script de seeding para crear datos de prueba completos.
Crea: empresa APPROVED → pista → disponibilidades → coach APPROVED → servicios → coach availability

Uso:
  1. Asegúrate de que el backend está corriendo (http://localhost:8000)
  2. Ejecuta: python seed_test_data.py
"""

import requests
import json
from datetime import date, timedelta
import sys

BASE_URL = "http://localhost:8000/api/v1"

# Colores para output
class Color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def log_header(msg):
    print(f"\n{Color.HEADER}{Color.BOLD}{'='*70}{Color.ENDC}")
    print(f"{Color.HEADER}{Color.BOLD}{msg}{Color.ENDC}")
    print(f"{Color.HEADER}{Color.BOLD}{'='*70}{Color.ENDC}\n")

def log_step(msg):
    print(f"{Color.CYAN}→ {msg}{Color.ENDC}")

def log_success(msg):
    print(f"{Color.GREEN}✅ {msg}{Color.ENDC}")

def log_error(msg):
    print(f"{Color.RED}❌ {msg}{Color.ENDC}")

def log_warning(msg):
    print(f"{Color.YELLOW}⚠️  {msg}{Color.ENDC}")

def log_info(msg):
    print(f"{Color.BLUE}ℹ️  {msg}{Color.ENDC}")

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

# ═════════════════════════════════════════════════════════════════════════════
# STEP 1: Verificar que backend está disponible
# ═════════════════════════════════════════════════════════════════════════════

log_header("VERIFICANDO CONECTIVIDAD")

try:
    resp = requests.get(f"{BASE_URL}/health", timeout=2)
    log_success(f"Backend disponible en {BASE_URL}")
except Exception as e:
    log_error(f"No se puede conectar al backend en {BASE_URL}")
    log_error(f"Error: {e}")
    sys.exit(1)

# ═════════════════════════════════════════════════════════════════════════════
# STEP 2: Obtener o crear ADMIN (para aprobar empresa y coach)
# ═════════════════════════════════════════════════════════════════════════════

log_header("OBTENIENDO CREDENCIALES DE ADMIN")

# Intentar login con credenciales de admin por defecto
admin_token = None
admin_id = None

resp = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "admin@motocross.com", "password": "Admin1234!"}
)

if resp.status_code == 200:
    admin_token = resp.json().get("token")
    admin_id = resp.json().get("user", {}).get("id")
    log_success(f"Admin encontrado (id={admin_id})")
else:
    log_error("No se pudo autenticar como admin")
    log_info(f"Credenciales intentadas: admin@motocross.com / Admin1234!")
    log_info(f"Respuesta: {resp.status_code} - {resp.text}")
    sys.exit(1)

# ═════════════════════════════════════════════════════════════════════════════
# STEP 3: Crear EMPRESA de prueba
# ═════════════════════════════════════════════════════════════════════════════

log_header("CREANDO EMPRESA DE PRUEBA")

import time
timestamp = str(int(time.time()))[-6:]  # Últimos 6 dígitos del timestamp
company_email = f"motocross-{timestamp}@test.example.com"
company_password = "Company1234!"
company_id = None
company_token = None

log_step(f"Registrando empresa con email {company_email}")

resp = requests.post(
    f"{BASE_URL}/auth/register-company",
    json={
        "email": company_email,
        "password": company_password,
        "nombre": "Juan García",
        "nombre_empresa": "Motocross Latin American Tours",
        "telefono": "+56912345678",
    }
)

if resp.status_code == 201:
    company_id = resp.json().get("id")
    log_success(f"Empresa registrada (id={company_id}, status=PENDING)")
elif resp.status_code == 400:
    # Ya existe, buscarla por email
    log_warning("Empresa ya existe en la BD")
    # Obtener el ID de la empresa existente consultando directamente
    # Para eso usamos una búsqueda o asumimos que ya está aprobada
    # Por ahora, continuamos con el email
    company_id = None
else:
    log_error(f"Error registrando empresa: {resp.status_code}")
    log_error(resp.text)
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Aprobar empresa (como admin)
# ─────────────────────────────────────────────────────────────────────────────

if company_id:
    log_step("Aprobando empresa como admin")
    
    resp = requests.put(
        f"{BASE_URL}/admin/companies/{company_id}/approve",
        headers=auth_headers(admin_token)
    )
    
    if resp.status_code == 200:
        log_success(f"Empresa aprobada")
    else:
        if "already approved" in resp.text.lower():
            log_warning("Empresa ya estaba aprobada")
        else:
            log_error(f"Error aprobando empresa: {resp.status_code}")
            log_info(f"Response: {resp.text}")

# Login con la empresa (después de aprobarla)
company_token = None
resp = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": company_email, "password": company_password}
)

if resp.status_code == 200:
    company_id = resp.json().get("user", {}).get("id")
    company_token = resp.json().get("token")
    log_success(f"Login de empresa exitoso (id={company_id})")
else:
    log_error(f"Error en login de empresa: {resp.status_code}")
    log_error(resp.text)
    sys.exit(1)

if company_token:
    log_info(f"Token de empresa: {company_token[:20]}...")
else:
    log_error("No se pudo obtener token de empresa")
    sys.exit(1)

# ═════════════════════════════════════════════════════════════════════════════
# STEP 4: Crear PISTA
# ═════════════════════════════════════════════════════════════════════════════

log_header("CREANDO PISTA")

track_id = None

track_payload = {
    "name": "Pista Motocross Central",
    "description": "Pista profesional con saltos, giros y obstáculos. Abierta todos los días.",
    "latitude": -33.894,
    "longitude": -70.1699,
    "price_junior": 50,
    "price_senior": 80,
    "price_junior_half": 30,
    "price_senior_half": 50,
    "difficulty_level": "INTERMEDIATE",
    "capacity": 15,
}

log_step(f"Creando pista: {track_payload['name']}")

resp = requests.post(
    f"{BASE_URL}/tracks",
    json=track_payload,
    headers=auth_headers(company_token)
)

if resp.status_code == 201:
    track_id = resp.json().get("id")
    log_success(f"Pista creada (id={track_id})")
elif resp.status_code == 400 and "already exists" in resp.text.lower():
    log_warning("Pista ya existe")
    # Obtener lista de pistas
    resp = requests.get(
        f"{BASE_URL}/companies/tracks",
        headers=auth_headers(company_token)
    )
    if resp.status_code == 200:
        tracks = resp.json()
        if tracks:
            track_id = tracks[0].get("id")
            log_success(f"Usando pista existente (id={track_id})")
else:
    log_error(f"Error creando pista: {resp.status_code}")
    log_error(resp.text)
    sys.exit(1)

# ═════════════════════════════════════════════════════════════════════════════
# STEP 5: Crear DISPONIBILIDADES de PISTA (para próximos 7 días)
# ═════════════════════════════════════════════════════════════════════════════

log_header("CREANDO DISPONIBILIDADES DE PISTA")

# Crear disponibilidades para los próximos 30 días
today = date.today()
dates_to_create = [today + timedelta(days=i) for i in range(1, 31)]

availability_count = 0

# Primero, traer las disponibilidades existentes
resp = requests.get(
    f"{BASE_URL}/tracks/{track_id}/availability",
    headers=auth_headers(company_token)
)

existing_availabilities = resp.json() if resp.status_code == 200 else []
existing_dates = set(a.get("date") for a in existing_availabilities)

log_info(f"Disponibilidades existentes: {len(existing_availabilities)}")
log_info(f"Creando disponibilidades para: {dates_to_create[0].strftime('%Y-%m-%d')} al {dates_to_create[-1].strftime('%Y-%m-%d')}")

for target_date in dates_to_create:
    date_str = target_date.strftime("%Y-%m-%d")
    
    if date_str in existing_dates:
        log_warning(f"  {date_str}: ya tiene disponibilidad")
        continue
    
    # Crear 2 slots por día: mañana y tarde
    slots = [
        {
            "date": date_str,
            "startTime": "09:00",
            "endTime": "13:00",
            "capacity": 12,
            "rentalType": "HALF_DAY",
            "pilotCategory": "BOTH"
        },
        {
            "date": date_str,
            "startTime": "14:00",
            "endTime": "18:00",
            "capacity": 12,
            "rentalType": "HALF_DAY",
            "pilotCategory": "BOTH"
        },
    ]
    
    for slot in slots:
        resp = requests.post(
            f"{BASE_URL}/tracks/{track_id}/availability",
            json=slot,
            headers=auth_headers(company_token)
        )
        
        if resp.status_code == 201:
            log_success(f"  {date_str} {slot['startTime']}-{slot['endTime']}: creada")
            availability_count += 1
        elif resp.status_code == 409:
            log_warning(f"  {date_str} {slot['startTime']}-{slot['endTime']}: solapamiento")
        else:
            log_error(f"  {date_str}: error {resp.status_code}")
            log_info(f"    {resp.text[:100]}")

log_info(f"Total de disponibilidades creadas: {availability_count}")

# ═════════════════════════════════════════════════════════════════════════════
# STEP 6: Crear COACH de prueba
# ═════════════════════════════════════════════════════════════════════════════

log_header("CREANDO COACH DE PRUEBA")

coach_email = f"coach-{timestamp}@test.example.com"
coach_password = "Coach1234!"
coach_id = None
coach_token = None

log_step(f"Registrando coach con email {coach_email}")

resp = requests.post(
    f"{BASE_URL}/auth/register-coach",
    json={
        "email": coach_email,
        "password": coach_password,
        "nombre": "Carlos Mendez",
        "licencia": "LICENSE-2024-001",
        "especialidad": "Cross Country",
        "telefono": "+56987654321",
    }
)

if resp.status_code == 201:
    coach_id = resp.json().get("id")
    log_success(f"Coach registrado (id={coach_id}, status=PENDING)")
elif resp.status_code == 400:
    log_warning("Coach ya existe en la BD")
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": coach_email, "password": coach_password}
    )
    if resp.status_code == 200:
        coach_id = resp.json().get("user", {}).get("id")
        coach_token = resp.json().get("token")
        log_success(f"Usando coach existente (id={coach_id})")
else:
    log_error(f"Error registrando coach: {resp.status_code}")
    log_error(resp.text)
    sys.exit(1)

# Login con el coach
if not coach_token:
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": coach_email, "password": coach_password}
    )
    coach_token = resp.json().get("token")

log_info(f"Token de coach: {coach_token[:20]}...")

# ─────────────────────────────────────────────────────────────────────────────
# Aprobar coach (como admin)
# ─────────────────────────────────────────────────────────────────────────────

log_step("Aprobando coach como admin")

resp = requests.put(
    f"{BASE_URL}/admin/verify-provider/{coach_id}",
    json={"providerType": "COACH", "status": "APPROVED"},
    headers=auth_headers(admin_token)
)

if resp.status_code == 200:
    log_success(f"Coach aprobado")
else:
    if "already approved" in resp.text.lower():
        log_warning("Coach ya estaba aprobado")
    else:
        log_error(f"Error aprobando coach: {resp.status_code}")
        log_info(f"Response: {resp.text}")

# ═════════════════════════════════════════════════════════════════════════════
# STEP 7-8: Asignar COACH a PISTA y crear SERVICIOS (combined via /coach/settings)
# ═════════════════════════════════════════════════════════════════════════════

log_header("CONFIGURANDO COACH: TRACKS Y SERVICIOS")

services = [
    {
        "classType": "HOURLY",
        "mode": "ONE_TO_ONE",
        "price": 60,
    },
    {
        "classType": "HOURLY",
        "mode": "GROUP",
        "price": 35,
        "maxStudents": 5,
    },
    {
        "classType": "HALF_DAY",
        "mode": "ONE_TO_ONE",
        "price": 200,
    },
    {
        "classType": "FULL_DAY",
        "mode": "ONE_TO_ONE",
        "price": 350,
    },
]

settings_payload = {
    "tracks": [{"trackId": track_id}],
    "services": services
}

log_step(f"Asignando track {track_id} y {len(services)} servicios al coach")

resp = requests.put(
    f"{BASE_URL}/coach/settings",
    json=settings_payload,
    headers=auth_headers(coach_token)
)

if resp.status_code == 200:
    log_success(f"Coach configurado: {len(services)} servicios creados")
    services_created = len(services)
else:
    log_error(f"Error configurando coach: {resp.status_code}")
    log_info(f"Response: {resp.text}")
    services_created = 0

# ═════════════════════════════════════════════════════════════════════════════
# STEP 9: Crear DISPONIBILIDADES de COACH
# ═════════════════════════════════════════════════════════════════════════════

log_header("CREANDO DISPONIBILIDADES DE COACH")

coach_availability_count = 0

for target_date in dates_to_create:
    date_str = target_date.strftime("%Y-%m-%d")
    
    # Crear 2 slots por día: mañana y tarde
    slots = [
        {
            "trackId": track_id,
            "date": date_str,
            "startTime": "09:00",
            "endTime": "13:00",
            "classType": "HALF_DAY",
            "mode": "ONE_TO_ONE",
        },
        {
            "trackId": track_id,
            "date": date_str,
            "startTime": "14:00",
            "endTime": "18:00",
            "classType": "HALF_DAY",
            "mode": "ONE_TO_ONE",
        },
    ]
    
    for slot in slots:
        resp = requests.post(
            f"{BASE_URL}/coach/availability",
            json=slot,
            headers=auth_headers(coach_token)
        )
        
        if resp.status_code == 201:
            log_success(f"  {date_str} {slot['startTime']}-{slot['endTime']}: creada")
            coach_availability_count += 1
        elif resp.status_code == 409:
            log_warning(f"  {date_str} {slot['startTime']}-{slot['endTime']}: solapamiento")
        else:
            log_error(f"  {date_str}: error {resp.status_code}")
            log_info(f"    {resp.text[:100]}")

log_info(f"Total de disponibilidades de coach creadas: {coach_availability_count}")

# ═════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════════════════════════

log_header("RESUMEN DE SEEDING")

log_info(f"Empresa: id={company_id}, email={company_email}, status=APPROVED")
log_info(f"Pista: id={track_id}, name={track_payload['name']}")
log_info(f"Disponibilidades de pista creadas: {availability_count}")
log_info(f"Coach: id={coach_id}, email={coach_email}, status=APPROVED")
log_info(f"Servicios del coach creados: {services_created}")
log_info(f"Disponibilidades de coach creadas: {coach_availability_count}")

log_header("PRÓXIMOS PASOS PARA PROBAR")

log_info("1. Abre el mapa en la app: debería ver la pista")
log_info("2. Haz clic en la pista → debería ver los coaches (Carlos Mendez)")
log_info("3. Haz clic en 'Agendar sin instructor' → debería ver disponibilidades")
log_info(f"4. Haz clic en 'Agendar con {services[0]['classType']}'")
log_info("5. Selecciona fecha/hora y confirma → debería ver cotización")

print()
