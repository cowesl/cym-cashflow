"""
CYM Materiales SA — Cash Flow
Módulo: Base de Datos (Supabase)
v3.0
"""

import hashlib
import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://pttwktanhoxohnfxiafu.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB0dHdrdGFuaG94b2huZnhpYWZ1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYwOTI5NjgsImV4cCI6MjA5MTY2ODk2OH0.aIH493PLy7HcfKBUcITYUAIo2gPzuljGH3hxI4OJJBk")

_client: Client = None

def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client

def init_db():
    sb = get_client()
    try:
        res = sb.table("usuarios").select("id").eq("username", "admin").execute()
        if not res.data:
            pwd_hash = hashlib.sha256("cym2026".encode()).hexdigest()
            sb.table("usuarios").insert({
                "username": "admin", "password_hash": pwd_hash,
                "rol": "admin", "nombre": "Administrador"
            }).execute()
    except Exception:
        pass

def _rows(res) -> list:
    return res.data or []

# ── Laborales ──────────────────────────────────────────────────────────────

def get_laborales():
    return _rows(get_client().table("egresos_laborales").select("*").order("concepto").execute())

def insert_laboral(concepto, organismo, monto, regla):
    get_client().table("egresos_laborales").insert({"concepto": concepto, "organismo": organismo, "monto": monto, "regla": regla}).execute()

def update_laboral(id_, monto, regla, activo):
    get_client().table("egresos_laborales").update({"monto": monto, "regla": regla, "activo": int(activo)}).eq("id", id_).execute()

def delete_laboral(id_):
    get_client().table("egresos_laborales").delete().eq("id", id_).execute()

def seed_laborales_default():
    sb = get_client()
    if sb.table("egresos_laborales").select("id").execute().data:
        return
    defaults = [
        ("Sueldos 1° Quincena","CYM",40_000_000,"d16"),
        ("Sueldos 2° Quincena","CYM",40_000_000,"d01"),
        ("Sueldos Mensuales","CYM",90_000_000,"penultimo_habil"),
        ("Edenred","CYM",15_000_000,"d05"),
        ("OSDE","CYM",8_000_000,"d15"),
        ("Cargas Sociales (931+Sind.)","ARCA",60_000_000,"arca"),
        ("Aguinaldo","CYM",85_000_000,"aguinaldo"),
    ]
    for c,o,m,r in defaults:
        sb.table("egresos_laborales").insert({"concepto":c,"organismo":o,"monto":m,"regla":r}).execute()

# ── Financieros ────────────────────────────────────────────────────────────

def get_financieros(solo_confirmados=False):
    q = get_client().table("egresos_financieros").select("*").order("fecha_pago_habil")
    if solo_confirmados:
        q = q.eq("es_estimado", 0)
    return _rows(q.execute())

def insert_financiero(banco, tipo, monto, monto_usd, fecha_venc, fecha_habil, origen_pdf, notas, es_estimado):
    res = get_client().table("egresos_financieros").insert({
        "banco": banco, "organismo": banco, "tipo": tipo, "monto": monto, "monto_usd": monto_usd,
        "fecha_vencimiento": fecha_venc, "fecha_pago_habil": fecha_habil,
        "origen_pdf": origen_pdf, "notas": notas, "es_estimado": es_estimado
    }).execute()
    return res.data[0]["id"] if res.data else None

def confirmar_financiero(id_):
    get_client().table("egresos_financieros").update({"es_estimado": 0}).eq("id", id_).execute()

def delete_financiero(id_):
    get_client().table("egresos_financieros").delete().eq("id", id_).execute()

def reemplazar_estimado(banco, tipo, monto, monto_usd, fecha_venc, fecha_habil, origen_pdf):
    sb = get_client()
    rows = sb.table("egresos_financieros").select("id").eq("tipo", tipo).eq("es_estimado", 1).execute()
    for r in (rows.data or []):
        sb.table("egresos_financieros").delete().eq("id", r["id"]).execute()

def reemplazar_confirmado(banco, tipo):
    sb = get_client()
    rows = sb.table("egresos_financieros").select("id").eq("tipo", tipo).eq("es_estimado", 0).execute()
    for r in (rows.data or []):
        sb.table("egresos_financieros").delete().eq("id", r["id"]).execute()

def update_financiero_desde_pdf(id_, monto, monto_usd, fecha_venc, fecha_habil):
    get_client().table("egresos_financieros").update({
        "monto": monto, "monto_usd": monto_usd,
        "fecha_vencimiento": fecha_venc, "fecha_pago_habil": fecha_habil
    }).eq("id", id_).execute()

# ── Préstamos ──────────────────────────────────────────────────────────────

def get_prestamos():
    return _rows(get_client().table("prestamos").select("*").order("concepto").execute())

def insert_prestamo(concepto, organismo, subtipo, monto, regla, fecha_ultima_cuota):
    get_client().table("prestamos").insert({"concepto":concepto,"organismo":organismo,"subtipo":subtipo,"monto":monto,"regla":regla,"fecha_ultima_cuota":fecha_ultima_cuota}).execute()

def update_prestamo(id_, monto, regla, fecha_ultima_cuota, activo):
    get_client().table("prestamos").update({"monto":monto,"regla":regla,"fecha_ultima_cuota":fecha_ultima_cuota,"activo":int(activo)}).eq("id", id_).execute()

def delete_prestamo(id_):
    get_client().table("prestamos").delete().eq("id", id_).execute()

def seed_prestamos_default():
    sb = get_client()
    if sb.table("prestamos").select("id").execute().data:
        return
    defaults = [
        ("Comercial 1","Banco Santander","prestamo",800_000,"d19","2030-12-31"),
        ("Comercial 2","Banco Santander","prestamo",500_000,"d13","2030-12-31"),
        ("Comercial 3","Banco Santander","prestamo",700_000,"d12","2030-12-31"),
        ("Galpón 1","Banco Bice","prestamo",1_700_000,"d08","2030-12-31"),
        ("Galpón 2","Banco Bice","prestamo",1_600_000,"d08","2030-12-31"),
        ("Galpón 3","Banco Bice","prestamo",150_000,"d08","2030-12-31"),
        ("Equipos Fundición","Banco Bice","prestamo",2_900_000,"d17","2030-12-31"),
        ("2021","Fondep","prestamo",400_000,"d01","2030-12-31"),
        ("Deuda Impositiva JJM","ARCA","plan_de_pago",100_000,"d16","2030-12-31"),
    ]
    for c,o,s,m,r,f in defaults:
        sb.table("prestamos").insert({"concepto":c,"organismo":o,"subtipo":s,"monto":m,"regla":r,"fecha_ultima_cuota":f}).execute()

# ── Impositivos ────────────────────────────────────────────────────────────

def get_impositivos():
    return _rows(get_client().table("egresos_impositivos").select("*").order("concepto").execute())

def insert_impositivo(concepto, organismo, monto, regla):
    get_client().table("egresos_impositivos").insert({"concepto":concepto,"organismo":organismo,"monto":monto,"regla":regla}).execute()

def update_impositivo(id_, monto, regla, activo):
    get_client().table("egresos_impositivos").update({"monto":monto,"regla":regla,"activo":int(activo)}).eq("id", id_).execute()

def delete_impositivo(id_):
    get_client().table("egresos_impositivos").delete().eq("id", id_).execute()

def seed_impositivos_default():
    sb = get_client()
    if sb.table("egresos_impositivos").select("id").execute().data:
        return
    defaults = [
        ("Autónomos","ARCA",0,"d20"),("Empleada Doméstica","ARCA",0,"d15"),("Monotributo","ARCA",0,"d20"),
        ("DREI - Corral de Bustos","COMARB",0,"d15"),("DREI - La Matanza","COMARB",0,"d14"),
        ("DREI - Soldini","COMARB",0,"d15"),("ISIB - Convenio Multilateral","COMARB",0,"d16"),
        ("ARBA - Retenciones Buenos Aires - Pago a Cuenta","ARBA",0,"d22"),
        ("ARBA - Retenciones Buenos Aires - Saldo","ARBA",0,"d10"),
        ("SICORE - Retenciones Ganancias - Pago a Cuenta","ARCA",0,"d22"),
        ("SICORE - Retenciones Ganancias - Saldo","ARCA",0,"d10"),
        ("SIRCAR - Retenciones Santa Fe - Pago a Cuenta","COMARB",0,"d22"),
        ("SIRCAR - Retenciones Santa Fe - Saldo","COMARB",0,"d06"),
    ]
    for c,o,m,r in defaults:
        sb.table("egresos_impositivos").insert({"concepto":c,"organismo":o,"monto":m,"regla":r}).execute()

# ── Proveedores ────────────────────────────────────────────────────────────

def get_proveedores():
    return _rows(get_client().table("proveedores").select("*").order("nombre").execute())

def insert_proveedor(codigo, nombre, categoria, monto, regla, regla2=""):
    get_client().table("proveedores").insert({"codigo":codigo,"nombre":nombre,"categoria":categoria,"monto":monto,"regla":regla,"regla2":regla2}).execute()

def update_proveedor(id_, categoria, monto, regla, regla2, activo):
    get_client().table("proveedores").update({"categoria":categoria,"monto":monto,"regla":regla,"regla2":regla2,"activo":int(activo)}).eq("id", id_).execute()

def delete_proveedor(id_):
    get_client().table("proveedores").delete().eq("id", id_).execute()

def seed_proveedores_default():
    pass

# ── Aduanero ───────────────────────────────────────────────────────────────

def get_aduanero():
    return _rows(get_client().table("aduanero").select("*").order("proveedor").execute())

def insert_aduanero(codigo, proveedor, monto_usd, vencimiento):
    get_client().table("aduanero").insert({"codigo":codigo,"proveedor":proveedor,"monto_usd":monto_usd,"vencimiento":vencimiento}).execute()

def update_aduanero(id_, monto_usd, vencimiento, activo):
    get_client().table("aduanero").update({"monto_usd":monto_usd,"vencimiento":vencimiento,"activo":int(activo)}).eq("id", id_).execute()

def delete_aduanero(id_):
    get_client().table("aduanero").delete().eq("id", id_).execute()

# ── Plazos Fijos ───────────────────────────────────────────────────────────

def get_plazos_fijos():
    return _rows(get_client().table("plazos_fijos").select("*").order("vencimiento").execute())

def insert_plazo_fijo(banco, monto, vencimiento, notas=""):
    get_client().table("plazos_fijos").insert({"banco":banco,"monto":monto,"vencimiento":vencimiento,"notas":notas}).execute()

def update_plazo_fijo(id_, banco, monto, vencimiento, notas=""):
    get_client().table("plazos_fijos").update({"banco":banco,"monto":monto,"vencimiento":vencimiento,"notas":notas}).eq("id", id_).execute()

def delete_plazo_fijo(id_):
    get_client().table("plazos_fijos").delete().eq("id", id_).execute()

# ── Usuarios ───────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_usuario(username: str, password: str):
    res = get_client().table("usuarios").select("*").eq("username", username).eq("activo", 1).execute()
    if not res.data:
        return None
    u = res.data[0]
    if u["password_hash"] == hash_password(password):
        return u
    return None

def get_usuarios():
    return _rows(get_client().table("usuarios").select("*").order("username").execute())

def insert_usuario(username, password, rol, nombre):
    get_client().table("usuarios").insert({"username":username,"password_hash":hash_password(password),"rol":rol,"nombre":nombre}).execute()

def update_usuario_password(id_, new_password):
    get_client().table("usuarios").update({"password_hash":hash_password(new_password)}).eq("id", id_).execute()

def update_usuario_activo(id_, activo):
    get_client().table("usuarios").update({"activo":int(activo)}).eq("id", id_).execute()

def delete_usuario(id_):
    get_client().table("usuarios").delete().eq("id", id_).neq("rol", "admin").execute()

def get_proximos_vencimientos(dias=30):
    return []
