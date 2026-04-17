"""
CYM Materiales SA — Cash Flow
Módulo: Lógica de Negocio
v2.9
"""

import calendar
from datetime import date, timedelta
from typing import Optional
from pdf_extractor import FERIADOS_AR, siguiente_dia_habil


# ── Monotributo: valores publicados por ARCA (Cat. B + Cat. C, col. 7 — Locaciones/Servicios) ──
# Vence el día 3 del MISMO mes del período devengado (CUIT termina en 2)
MONOTRIBUTO_VALORES = {
    # Ago 2025 – Ene 2026: B=$7946.95 + C=$13663.17
    (2025, 8):  round(7946.95 + 13663.17, 2),
    (2025, 9):  round(7946.95 + 13663.17, 2),
    (2025, 10): round(7946.95 + 13663.17, 2),
    (2025, 11): round(7946.95 + 13663.17, 2),
    (2025, 12): round(7946.95 + 13663.17, 2),
    (2026, 1):  round(7946.95 + 13663.17, 2),   # 21610.12 — vence 3 ene 2026
    # Desde Feb 2026: B=$9082.88 + C=$15616.17
    (2026, 2):  round(9082.88 + 15616.17, 2),   # 24699.05 — vence 3 feb 2026
    (2026, 3):  round(9082.88 + 15616.17, 2),   # 24699.05 — vence 3 mar 2026 (mismos valores hasta nueva actualización)
    # Agregar nuevos meses cuando ARCA actualice
}

def get_monto_monotributo(anio: int, mes: int) -> float:
    """Retorna el monto de monotributo para el período (anio, mes). Usa el último conocido si no está publicado."""
    if (anio, mes) in MONOTRIBUTO_VALORES:
        return float(MONOTRIBUTO_VALORES[(anio, mes)])
    claves = sorted([k for k in MONOTRIBUTO_VALORES if k <= (anio, mes)], reverse=True)
    if claves:
        return float(MONOTRIBUTO_VALORES[claves[0]])
    if MONOTRIBUTO_VALORES:
        return float(list(MONOTRIBUTO_VALORES.values())[0])
    return 0.0

def calcular_fecha_monotributo(anio: int, mes: int) -> date:
    """Monotributo vence el día 20 del MISMO mes (CUIT termina en 2)."""
    return siguiente_dia_habil(date(anio, mes, 20))


# ── Empleada Doméstica: valores publicados por ARCA (16 o más hs semanales, mayor 18 años) ──
# Clave: (anio, mes) = monto total del período devengado
# Vence el día 10 del mes siguiente (o hábil siguiente)
# 2 trabajadoras de 16hs o más + 1 de menos de 12hs (mayor 18 años activa)
EMPLEADA_VALORES = {
    (2026, 1): 82933.68,    # (37095.95×2 + 8741.78)  — vence 10 feb 2026
    (2026, 2): 83355.13,    # (37271.19×2 + 8812.75)  — vence 10 mar 2026
    (2026, 3): 84605.46,   # (37280.16×2 + 8944.94) estimado +1.5% — vence 10 abr 2026
    # Agregar nuevos meses cuando ARCA publique el PDF oficial
}

def get_monto_empleada(anio: int, mes: int) -> float:
    if (anio, mes) in EMPLEADA_VALORES:
        return float(EMPLEADA_VALORES[(anio, mes)])
    claves = sorted([k for k in EMPLEADA_VALORES if k <= (anio, mes)], reverse=True)
    if claves:
        return float(EMPLEADA_VALORES[claves[0]])
    if EMPLEADA_VALORES:
        return float(list(EMPLEADA_VALORES.values())[0])
    return 0.0

def calcular_fecha_empleada(anio: int, mes: int) -> date:
    """Empleada doméstica vence el día 10 del mes siguiente al período devengado."""
    mes_venc  = mes % 12 + 1
    anio_venc = anio + (1 if mes == 12 else 0)
    return siguiente_dia_habil(date(anio_venc, mes_venc, 10))


# ── Autónomos: valores publicados por ARCA ────────────────────────────────
# Clave: (anio, mes) = monto total (2× Cat.V apt.A + 1× Cat.I apt.E)
AUTONOMOS_VALORES = {
    (2026, 1): round(276065.92 * 2 + 52939.47),   # vence 3 feb 2026
    (2026, 2): round(283933.80 * 2 + 54448.25),   # vence 3 mar 2026
    (2026, 3): round(292111.10 * 2 + 56016.36),   # vence 3 abr 2026
    # Cuando ARCA publique nuevos valores, agregar aquí:
}

def get_monto_autonomos(anio: int, mes: int) -> float:
    """
    Retorna el monto de autónomos para el período devengado (anio, mes).
    Si no está publicado, usa el último mes conocido.
    """
    if (anio, mes) in AUTONOMOS_VALORES:
        return float(AUTONOMOS_VALORES[(anio, mes)])
    # Buscar el último valor publicado anterior
    claves = sorted([k for k in AUTONOMOS_VALORES if k <= (anio, mes)], reverse=True)
    if claves:
        return float(AUTONOMOS_VALORES[claves[0]])
    # Si no hay nada anterior, usar el primero disponible
    if AUTONOMOS_VALORES:
        return float(list(AUTONOMOS_VALORES.values())[0])
    return 0.0


def calcular_fecha_autonomos(anio: int, mes: int) -> date:
    """
    Autónomos vencen el día 3 del mes SIGUIENTE al período devengado.
    CUIT terminado en 2 → día 3 (o hábil siguiente).
    """
    mes_venc = mes % 12 + 1
    anio_venc = anio + (1 if mes == 12 else 0)
    return siguiente_dia_habil(date(anio_venc, mes_venc, 3))

REGLA_LABEL = {
    "d01": "Día 1", "d05": "Día 5", "d08": "Día 8", "d10": "Día 10",
    "d12": "Día 12", "d13": "Día 13", "d15": "Día 15", "d16": "Día 16",
    "d17": "Día 17", "d19": "Día 19", "d20": "Día 20", "d25": "Día 25",
    "fin": "Fin de mes", "penultimo_habil": "Penúltimo día hábil",
    "arca": "ARCA (día 10)", "aguinaldo": "Aguinaldo (30/06 y 18/12)",
    "manual": "Fecha manual", "pdf": "Desde PDF",
}

REGLAS_DISPONIBLES = [
    "d01","d05","d08","d10","d12","d13","d15","d16",
    "d17","d19","d20","d25","fin","penultimo_habil","arca"
]

# Conceptos que usan fecha unificada (la más temprana entre los tres)
GRUPO_FECHA_UNIFICADA = {"Autónomos", "Empleada Doméstica", "Monotributo"}


def anterior_dia_habil(d: date) -> date:
    while d.weekday() >= 5 or d in FERIADOS_AR:
        d -= timedelta(days=1)
    return d


def dias_en_mes(anio: int, mes: int) -> int:
    return calendar.monthrange(anio, mes)[1]


def penultimo_dia_habil(anio: int, mes: int) -> date:
    ultimo_dia = dias_en_mes(anio, mes)
    habiles = []
    d = date(anio, mes, ultimo_dia)
    while len(habiles) < 2:
        if d.weekday() < 5 and d not in FERIADOS_AR:
            habiles.append(d)
        d -= timedelta(days=1)
    return habiles[1]


def calcular_fecha_pago(regla: str, anio: int, mes: int) -> Optional[date]:
    dias = dias_en_mes(anio, mes)
    mapa_dia = {
        "d01": 1, "d05": 5, "d06": 6, "d08": 8, "d10": 10, "d12": 12, "d13": 13,
        "d14": 14, "d15": 15, "d16": 16, "d17": 17, "d19": 19,
        "d20": 20, "d22": 22, "d25": 25,
    }
    if regla in mapa_dia:
        return siguiente_dia_habil(date(anio, mes, mapa_dia[regla]))
    elif regla.startswith("d") and regla[1:].isdigit():
        # Regla genérica dXX para cualquier día del mes
        dia = int(regla[1:])
        dias_mes = dias_en_mes(anio, mes)
        dia = min(dia, dias_mes)  # ajustar si el mes tiene menos días
        return siguiente_dia_habil(date(anio, mes, dia))
    elif regla == "arca":
        return siguiente_dia_habil(date(anio, mes, 10))
    elif regla == "fin":
        return siguiente_dia_habil(date(anio, mes, dias))
    elif regla == "penultimo_habil":
        return penultimo_dia_habil(anio, mes)
    elif regla == "aguinaldo":
        if mes == 6:
            return anterior_dia_habil(date(anio, 6, 30))
        elif mes == 12:
            return anterior_dia_habil(date(anio, 12, 18))
        return None
    return None


# Alias
calcular_fecha_laboral = calcular_fecha_pago


def generar_proyeccion_laborales(conceptos: list, meses: int = 6) -> list:
    hoy  = date.today()
    rows = []
    # Incluir mes anterior para capturar vencimientos que caen después de hoy
    # (ej: d01 de marzo genera fecha 1/4, que es futura)
    meses_extra = [-1] + list(range(meses))
    for c in conceptos:
        if not c.get("activo", True):
            continue
        for i in meses_extra:
            mes_base  = (hoy.month - 1 + i) % 12 + 1
            anio_base = hoy.year + ((hoy.month - 1 + i) // 12)
            fecha = calcular_fecha_pago(c["regla"], anio_base, mes_base)
            if fecha is None or fecha < hoy - timedelta(days=10):
                continue
            monto_final = c["monto"]
            if c.get("regla") == "arca" and mes_base in (1, 7):
                monto_final = round(c["monto"] * 1.5)
            rows.append({
                "fecha": fecha, "descripcion": c["concepto"],
                "monto": monto_final, "categoria": "Laboral",
            })
    # Eliminar duplicados por (fecha, descripcion)
    seen = set()
    unique = []
    for r in sorted(rows, key=lambda r: r["fecha"]):
        key = (r["fecha"], r["descripcion"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def generar_proyeccion_prestamos(prestamos: list, meses: int = 6) -> list:
    hoy  = date.today()
    rows = []
    for p in prestamos:
        if not p.get("activo", True):
            continue
        try:
            ultima = date.fromisoformat(p["fecha_ultima_cuota"])
        except (ValueError, TypeError):
            continue
        for i in ([-1] + list(range(meses))):
            mes_base  = (hoy.month - 1 + i) % 12 + 1
            anio_base = hoy.year + ((hoy.month - 1 + i) // 12)
            fecha = calcular_fecha_pago(p["regla"], anio_base, mes_base)
            if fecha is None or fecha > ultima:
                continue
            rows.append({
                "fecha": fecha,
                "descripcion": f"{p['concepto']} — {p['organismo']}",
                "concepto": p["concepto"],
                "organismo": p["organismo"],
                "subtipo": p.get("subtipo", "prestamo"),
                "monto": p["monto"],
                "categoria": "Financiero",
                "ultima_cuota": ultima,
            })
    return sorted(rows, key=lambda r: r["fecha"])


def generar_proyeccion_impositivos(conceptos: list, meses: int = 6,
                                    unificar_fechas: bool = False) -> list:
    """
    Proyecta impositivos.
    - Autónomos: vence día 3 mes siguiente. Monto: DB si >0, sino ARCA.
    - Empleada Doméstica: vence día 10 mes siguiente. Monto: DB si >0, sino ARCA.
    - Monotributo: vence día 20 mismo mes. Monto: DB si >0, sino ARCA.
    - Resto de conceptos: monto y regla de DB.
    - unificar_fechas=True: todos usan la fecha más temprana (dashboard).
    - unificar_fechas=False: cada uno usa su fecha real (módulo impositivo).
    Si ARCA no publicó el mes, usa el último mes conocido como provisorio.
    """
    hoy  = date.today()
    rows = []

    for i in range(meses):
        mes_base  = (hoy.month - 1 + i) % 12 + 1
        anio_base = hoy.year + ((hoy.month - 1 + i) // 12)

        # Período devengado = mes anterior (autónomos y empleada)
        mes_dev  = (mes_base - 2) % 12 + 1
        anio_dev = anio_base - (1 if mes_base == 1 else 0)

        # Fechas reales de cada concepto
        fecha_autonomos   = calcular_fecha_autonomos(anio_dev, mes_dev)
        fecha_empleada    = calcular_fecha_empleada(anio_dev, mes_dev)
        fecha_monotributo = calcular_fecha_monotributo(anio_base, mes_base)

        # Fecha unificada = la más temprana
        fecha_unificada = min(fecha_autonomos, fecha_empleada, fecha_monotributo)

        for c in conceptos:
            if not c.get("activo", True):
                continue

            if c["concepto"] == "AUTÓNOMOS":
                # Monto: DB si >0, sino ARCA
                monto = c.get("monto") or 0
                if not monto:
                    monto = get_monto_autonomos(anio_dev, mes_dev)
                fecha = fecha_unificada if unificar_fechas else fecha_autonomos
                rows.append({
                    "fecha": fecha, "descripcion": "AUTÓNOMOS",
                    "organismo": c.get("organismo", "ARCA"),
                    "monto": monto, "categoria": "Impositivo",
                })
                continue

            if c["concepto"] == "EMPLEADA DOMÉSTICA":
                monto = c.get("monto") or 0
                if not monto:
                    monto = get_monto_empleada(anio_dev, mes_dev)
                fecha = fecha_unificada if unificar_fechas else fecha_empleada
                rows.append({
                    "fecha": fecha, "descripcion": "EMPLEADA DOMÉSTICA",
                    "organismo": c.get("organismo", "ARCA"),
                    "monto": monto, "categoria": "Impositivo",
                })
                continue

            if c["concepto"] == "MONOTRIBUTO":
                monto = c.get("monto") or 0
                if not monto:
                    monto = get_monto_monotributo(anio_base, mes_base)
                fecha = fecha_unificada if unificar_fechas else fecha_monotributo
                rows.append({
                    "fecha": fecha, "descripcion": "MONOTRIBUTO",
                    "organismo": c.get("organismo", "ARCA"),
                    "monto": monto, "categoria": "Impositivo",
                })
                continue

            if c.get("monto", 0) == 0:
                continue

            fecha = calcular_fecha_pago(c["regla"], anio_base, mes_base)
            if fecha is None:
                continue

            rows.append({
                "fecha": fecha, "descripcion": c["concepto"],
                "organismo": c.get("organismo", "ARCA"),
                "monto": c["monto"], "categoria": "Impositivo",
            })

    return sorted(rows, key=lambda r: r["fecha"])


def generar_proyeccion_comercial(proveedores: list, meses: int = 6) -> list:
    """
    Proyecta pagos a proveedores recurrentes.
    Si regla2 está definida: dos pagos por mes (quincenal).
    Cada pago es por el monto completo.
    """
    hoy  = date.today()
    rows = []
    for p in proveedores:
        if not p.get("activo", True) or p.get("monto", 0) == 0:
            continue
        reglas = [p["regla"]]
        if p.get("regla2"):
            reglas.append(p["regla2"])
        for i in ([-1] + list(range(meses))):
            mes_base  = (hoy.month - 1 + i) % 12 + 1
            anio_base = hoy.year + ((hoy.month - 1 + i) // 12)
            for regla in reglas:
                fecha = calcular_fecha_pago(regla, anio_base, mes_base)
                if fecha is None:
                    continue
                rows.append({
                    "fecha":       fecha,
                    "descripcion": p["nombre"],
                    "codigo":      p.get("codigo", ""),
                    "monto":       p["monto"],
                    "categoria":   "Comercial",
                })
    return sorted(rows, key=lambda r: r["fecha"])


def fetch_proveedor(codigo: str) -> dict:
    """
    Puente para obtener el monto de la última factura del proveedor desde SQL Server.
    Por ahora retorna datos dummy. En producción: conectar a SQL Server con pyodbc.
    Ejemplo futuro:
        import pyodbc
        conn = pyodbc.connect(CONNECTION_STRING)
        cur  = conn.cursor()
        cur.execute("SELECT TOP 1 monto FROM cuentas_corrientes WHERE codigo=? ORDER BY fecha DESC", codigo)
        row = cur.fetchone()
        return {"codigo": codigo, "monto": row.monto if row else 0, "fuente": "sqlserver"}
    """
    return {"codigo": codigo, "monto": 0.0, "fuente": "dummy"}


def fetch_external_data(concepto: str, organismo: str = "ARCA") -> dict:
    """Puente para endpoint externo. Por ahora retorna datos dummy."""
    return {"concepto": concepto, "organismo": organismo, "monto": 0.0, "fecha": None, "fuente": "dummy"}
