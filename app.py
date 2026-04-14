"""
CYM MATERIALES SA — App de Cash Flow
Versión: 2.8.0
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
import io

import database as db
import pdf_extractor as pdf_ext
import business_logic as bl

DIAS_PASADO = 10
DIAS_FUTURO = 30

@st.cache_data(ttl=300)
def cached_proyeccion_laborales(conceptos_tuple):
    conceptos = [{"concepto": c[0], "monto": c[1], "regla": c[2], "activo": c[3]} for c in conceptos_tuple]
    return bl.generar_proyeccion_laborales(conceptos, meses=6)

@st.cache_data(ttl=300)
def cached_proyeccion_prestamos(prestamos_tuple):
    prestamos = [{"concepto": p[0], "organismo": p[1], "subtipo": p[2], "monto": p[3],
                  "regla": p[4], "fecha_ultima_cuota": p[5], "activo": p[6]} for p in prestamos_tuple]
    return bl.generar_proyeccion_prestamos(prestamos, meses=6)

@st.cache_data(ttl=300)
def cached_proyeccion_impositivos(conceptos_tuple, unificar=False):
    conceptos = [{"concepto": c[0], "organismo": c[1], "monto": c[2], "regla": c[3], "activo": c[4]} for c in conceptos_tuple]
    return bl.generar_proyeccion_impositivos(conceptos, meses=6, unificar_fechas=unificar)

@st.cache_data(ttl=300)
def cached_proyeccion_comercial(prov_tuple):
    proveedores = [{"codigo": p[0], "nombre": p[1], "monto": p[2], "regla": p[3], "regla2": p[4], "activo": p[5]} for p in prov_tuple]
    return bl.generar_proyeccion_comercial(proveedores, meses=6)

@st.cache_data(ttl=60)
def cached_get_financieros():
    return db.get_financieros(solo_confirmados=True)

MESES_ES = {
    1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",
    7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"
}
DIAS_ES = {0:"Lun",1:"Mar",2:"Mié",3:"Jue",4:"Vie",5:"Sáb",6:"Dom"}

def fmt_fecha(d: date) -> str:
    return f"{DIAS_ES[d.weekday()]} {d.day:02d}/{d.month:02d}/{d.year}"

def estado_egreso(fecha: date) -> dict:
    diff = (fecha - date.today()).days
    if diff < 0:
        return {"label": f"Vencido ({abs(diff)}d)", "color": "#D72B2B", "icono": "🔴"}
    elif diff == 0:
        return {"label": "Hoy",                      "color": "#D72B2B", "icono": "🔴"}
    elif diff <= 3:
        return {"label": f"Urgente ({diff}d)",       "color": "#D72B2B", "icono": "🔴"}
    elif diff <= 10:
        return {"label": f"Próximo ({diff}d)",       "color": "#e65100", "icono": "🟠"}
    else:
        return {"label": f"En {diff}d",              "color": "#2e7d32", "icono": "🟢"}

st.set_page_config(page_title="CYM Cash Flow", page_icon="💼", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Barlow', 'Gill Sans', Arial, sans-serif; }
.block-container { padding-top: 1rem !important; }
div[data-testid="stHorizontalBlock"] { gap: 0.5rem !important; }
div[data-testid="column"] > div { padding: 0 !important; }
hr { margin: 0.4rem 0 !important; }
/* Compactar filas de configuración */
div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] {
    margin-top: -12px !important;
    margin-bottom: -12px !important;
}
div[data-testid="stNumberInput"] {
    margin-bottom: 0px !important;
    padding-bottom: 0px !important;
}
div[data-testid="stTextInput"] {
    margin-bottom: 0px !important;
    padding-bottom: 0px !important;
}
div[data-testid="stSelectbox"] {
    margin-bottom: 0px !important;
    padding-bottom: 0px !important;
}
.dash-header {
    font-size: 18px !important;
    font-weight: 600 !important;
    color: #31333F !important;
    margin: 0 !important;
    padding: 0 !important;
    height: 25px;
    line-height: 25px;
}
.dash-date {
    font-size: 14px !important;
    color: #808495 !important;
    margin: 0 0 12px 0 !important;
    padding: 0 !important;
    height: 20px;
    line-height: 20px;
}
[data-testid="stMetricValue"] {
    font-size: 22px !important;
    font-weight: 700 !important;
    color: #1A1A1A !important;
}
[data-testid="stMetric"] { padding: 0 !important; }
[data-testid="stDataFrame"] td, [role="gridcell"] {
    padding-top: 0px !important;
    padding-bottom: 0px !important;
    line-height: 1 !important;
    font-size: 13px !important;
    font-weight: 400 !important;
}
div[data-testid="stDataFrame"] {
    font-size: 13px !important;
}
[data-testid="stHeader"] th, .stDataFrame thead tr th {
    font-size: 11px !important;
    color: #A0A0A0 !important;
    font-weight: 400 !important;
    text-transform: lowercase !important;
    padding-top: 2px !important;
    padding-bottom: 2px !important;
}
div[data-testid="column"]:nth-child(3) .hasta-row {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    gap: 8px !important;
}
div[data-testid="column"]:nth-child(3) div[data-testid="stDateInput"] {
    margin-top: 0px !important;
    flex: 1;
}
.hasta-text {
    font-size: 0.7rem;
    font-weight: 700;
    color: #D72B2B;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    white-space: nowrap;
    margin: 0 !important;
    padding-bottom: 6px;
}
.cym-header { display:flex;align-items:center;gap:20px;padding:4px 0;
    margin-bottom:0.5rem;border-bottom:2px solid #D72B2B; }
.cym-header-text h1 { font-size:1.3rem;font-weight:700;color:#1A1A1A;margin:0; }
.cym-header-text p  { font-size:.8rem;color:#6B6B6B;margin:0;text-transform:uppercase;letter-spacing:.8px; }
.kpi-card { background:#F5F5F5;border:1px solid #E0E0E0;padding:1rem 1.2rem; }
.kpi-card .label { font-size:.7rem;color:#6B6B6B;text-transform:uppercase;letter-spacing:1px; }
.kpi-card .value { font-size:1.6rem;font-weight:700;color:#1A1A1A; }
.kpi-card .sub   { font-size:.7rem;color:#6B6B6B;margin-top:2px; }
.sec-title { font-size:.7rem;font-weight:700;color:#D72B2B;text-transform:uppercase;
    letter-spacing:1.2px;border-bottom:1px solid #E0E0E0;padding-bottom:6px;margin-bottom:.8rem; }
.estimado { background:#fff8e1;border-left:3px solid #e65100;padding:2px 6px;
    font-size:.75rem;color:#e65100;font-weight:600; }
thead tr th { background:#D72B2B !important;color:white !important;font-size:.75rem !important; }
</style>
""", unsafe_allow_html=True)

db.init_db()
db.seed_laborales_default()

# ── Login / Sesión ────────────────────────────────────────────────────────
if "usuario_logueado" not in st.session_state:
    st.session_state.usuario_logueado = None

if st.session_state.usuario_logueado is None:
    st.markdown("""
        <div style='max-width:360px;margin:80px auto 0;'>
        <h2 style='text-align:center;color:#D72B2B;font-size:22px;margin-bottom:24px'>
        CYM Materiales — Cash Flow</h2>
        </div>""", unsafe_allow_html=True)
    with st.form("login_form"):
        st.markdown("#### Iniciar sesión")
        usr = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Ingresar", use_container_width=True)
        if submitted:
            u = db.verificar_usuario(usr, pwd)
            if u:
                st.session_state.usuario_logueado = u
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    st.stop()

# Usuario logueado
_usr = st.session_state.usuario_logueado
_es_admin = _usr["rol"] == "admin"

# Botón logout en sidebar
with st.sidebar:
    st.markdown(f"**{_usr['nombre'] or _usr['username']}**")
    st.caption(f"Rol: {_usr['rol']}")
    if st.button("Cerrar sesión"):
        st.session_state.usuario_logueado = None
        st.rerun()
db.seed_impositivos_default()
db.seed_prestamos_default()
db.seed_proveedores_default()

# Corrección automática de reglas (Supabase)
try:
    _lab_rows = db.get_laborales()
    for _r in _lab_rows:
        if _r["concepto"] == "Sueldos Mensuales" and _r["regla"] != "penultimo_habil":
            db.update_laboral(_r["id"], _r["monto"], "penultimo_habil", _r.get("activo", 1))
except Exception:
    pass

# Migración impositivos: cargar nuevos si no están
try:
    db.seed_impositivos_default()
except Exception:
    pass

st.markdown("""
<div class="cym-header">
    <div class="cym-header-text">
        <h1>CYM Materiales SA — Cash Flow</h1>
        <p>Gestión de Egresos · Laborales + Financieros + Impositivos · v2.8</p>
    </div>
</div>
""", unsafe_allow_html=True)

tabs_lista = ["📊 Dashboard", "🏦 (E) Financieros", "🧾 (E) Impositivos", "👷 (E) Laborales", "🏪 (E) Servicios", "🚢 (E) Aduaneros", "💰 (I) Plazos Fijos"]
if _es_admin:
    tabs_lista.append("👤 Usuarios")

tabs_result = st.tabs(tabs_lista)
tab_dash = tabs_result[0]
tab_fin  = tabs_result[1]
tab_imp  = tabs_result[2]
tab_lab  = tabs_result[3]
tab_com  = tabs_result[4]
tab_adu  = tabs_result[5]
tab_ing  = tabs_result[6]
tab_usr  = tabs_result[7] if _es_admin else None


# ═══════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD (calendario semanal)
# ═══════════════════════════════════════════════════════════════
with tab_dash:
    hoy = date.today()

    # ── Colores por categoría ─────────────────────────────────
    CAT_COLORES = {
        "Laboral":    {"bg": "#EAF3DE", "fg": "#27500A", "borde": "#639922"},
        "Financiero": {"bg": "#FCEBEB", "fg": "#791F1F", "borde": "#E24B4A"},
        "Impositivo": {"bg": "#FAEEDA", "fg": "#633806", "borde": "#EF9F27"},
        "Aduanero":   {"bg": "#FFF9C4", "fg": "#5a4500", "borde": "#D4AC17"},
        "Comercial":  {"bg": "#E6F1FB", "fg": "#0C447C", "borde": "#378ADD"},
        "Vencido":    {"bg": "#F1EFE8", "fg": "#5F5E5A", "borde": "#888780"},
    }

    # ── Datos ─────────────────────────────────────────────────
    laborales_db  = db.get_laborales()
    financieros_c = db.get_financieros(solo_confirmados=True)

    lab_tuple = tuple((r["concepto"], r["monto"], r["regla"], bool(r["activo"])) for r in laborales_db)
    proj_lab = cached_proyeccion_laborales(lab_tuple)

    # Préstamos
    prestamos_db_dash = db.get_prestamos()
    prest_tuple = tuple((p["concepto"], p["organismo"], p.get("subtipo","prestamo"),
                         p["monto"], p["regla"], p["fecha_ultima_cuota"], bool(p["activo"]))
                        for p in prestamos_db_dash)
    proj_prest_dash = cached_proyeccion_prestamos(prest_tuple)

    # Impositivos
    impositivos_db_dash = db.get_impositivos()
    imp_tuple = tuple((r["concepto"], r["organismo"], r["monto"], r["regla"], bool(r["activo"])) for r in impositivos_db_dash)
    proj_imp_dash = cached_proyeccion_impositivos(imp_tuple, unificar=True)

    # Armar lista unificada de egresos
    todos_egresos = []
    for r in proj_lab:
        todos_egresos.append({
            "fecha": r["fecha"], "cat": "Laboral",
            "desc": r["descripcion"], "monto": r["monto"],
            "monto_usd": 0.0, "est": False,
        })
    for f in financieros_c:
        try:
            fp = date.fromisoformat(f["fecha_pago_habil"])
        except (ValueError, TypeError):
            continue
        # Formato nombre tarjeta: "Visa Santander", "Cabal Credicoop", etc.
        banco_corto = f["organismo"].replace("Banco ","").replace("banco ","")
        desc_tar = f"{f['tipo']} {banco_corto}"
        todos_egresos.append({
            "fecha": fp, "cat": "Financiero",
            "desc": desc_tar,
            "monto": f["monto"],
            "monto_usd": f.get("monto_usd") or 0.0,
            "est": bool(f.get("es_estimado")),
        })
    for r in proj_prest_dash:
        org_corto = r["organismo"].replace("Banco ","").replace("banco ","")
        prefijo = "Plan" if r.get("subtipo") == "plan_de_pago" else "Prest"
        desc_p = f"{prefijo} {org_corto} {r['concepto']}"
        todos_egresos.append({
            "fecha": r["fecha"], "cat": "Financiero",
            "desc": desc_p, "monto": r["monto"],
            "monto_usd": 0.0, "est": False,
        })
    for r in proj_imp_dash:
        todos_egresos.append({
            "fecha": r["fecha"], "cat": "Impositivo",
            "desc": r["descripcion"], "monto": r["monto"],
            "monto_usd": 0.0, "est": False,
        })

    # Comerciales
    proveedores_db_dash = db.get_proveedores()
    prov_tuple_dash = tuple((p["codigo"], p["nombre"], p["monto"], p["regla"], p.get("regla2",""), bool(p["activo"])) for p in proveedores_db_dash)
    proj_com_dash = cached_proyeccion_comercial(prov_tuple_dash)
    for r in proj_com_dash:
        codigo_str = f"{r['codigo']} " if r.get("codigo") else ""
        todos_egresos.append({
            "fecha": r["fecha"], "cat": "Comercial",
            "desc": f"{codigo_str}{r['descripcion']}", "monto": r["monto"],
            "monto_usd": 0.0, "est": False,
        })
    # Aduanero — vencimientos con fecha específica, monto en U$S
    aduanero_db_dash = db.get_aduanero()
    desde_adu = date.today() - timedelta(days=DIAS_PASADO)
    for reg in aduanero_db_dash:
        if not reg.get("activo", True) or not reg.get("vencimiento"):
            continue
        try:
            fecha_adu = date.fromisoformat(reg["vencimiento"])
        except Exception:
            continue
        if fecha_adu < desde_adu:
            continue
        codigo_str = f"{reg['codigo']} " if reg.get("codigo") else ""
        todos_egresos.append({
            "fecha": fecha_adu, "cat": "Aduanero",
            "desc": f"{codigo_str}{reg['proveedor']}",
            "monto": 0.0,
            "monto_usd": float(reg["monto_usd"]),
            "est": False,
        })
    todos_egresos.sort(key=lambda x: x["fecha"])

    # ── KPIs globales (±30 días) ───────────────────────────────
    desde_kpi = hoy - timedelta(days=30)
    hasta_kpi = hoy + timedelta(days=30)
    win = [e for e in todos_egresos if desde_kpi <= e["fecha"] <= hasta_kpi]
    total_ars = sum(e["monto"] for e in win)
    total_lab = sum(e["monto"] for e in win if e["cat"]=="Laboral")
    total_fin = sum(e["monto"] for e in win if e["cat"]=="Financiero")
    total_usd = sum(e["monto_usd"] for e in win)

    st.markdown("---")

    # ── Semana en navegación ──────────────────────────────────
    if "sem_offset" not in st.session_state:
        st.session_state.sem_offset = 0
    if "hasta_fecha" not in st.session_state:
        st.session_state.hasta_fecha = hoy + timedelta(days=30)

    def lunes_de(base, offset):
        dia = base.weekday()  # 0=lun
        return base - timedelta(days=dia) + timedelta(weeks=offset)

    lunes_sem = lunes_de(hoy, st.session_state.sem_offset)
    dias_semana = [lunes_sem + timedelta(days=i) for i in range(7)]
    domingo_sem = dias_semana[6]

    # ── Etiqueta semana actual ──────────────────────────────────
    def domingo_siguiente(d):
        dia = d.weekday()
        return d + timedelta(days=(6 - dia))
    dom_esta_sem = domingo_siguiente(hoy)

    if hoy.month == dom_esta_sem.month:
        label_sem = f"{hoy.day} – {dom_esta_sem.day} {MESES_ES[hoy.month]}"
    else:
        label_sem = f"{hoy.day} {MESES_ES[hoy.month]} – {dom_esta_sem.day} {MESES_ES[dom_esta_sem.month]}"

    # ── Cálculo de totales por período ──────────────────────────
    def calcular_totales_cat(evs):
        cats = {}
        total_ars = 0
        total_usd = 0
        for e in evs:
            cats[e["cat"]] = cats.get(e["cat"], 0) + e["monto"]
            total_ars += e["monto"]
            total_usd += e.get("monto_usd", 0)
        return total_ars, total_usd, cats

    h0 = hoy
    dom_sem = dom_esta_sem
    fh_calc = st.session_state.hasta_fecha
    fh_calc_end = fh_calc

    manana   = h0 + timedelta(days=1)
    # Lunes siguiente al domingo de esta semana
    lunes_sig = dom_sem + timedelta(days=1)

    ev_hoy   = [e for e in todos_egresos if e["fecha"] == h0]
    ev_sem   = [e for e in todos_egresos if manana <= e["fecha"] <= dom_sem]
    ev_hasta = [e for e in todos_egresos if lunes_sig <= e["fecha"] <= fh_calc_end]

    t_hoy,   u_hoy,   c_hoy   = calcular_totales_cat(ev_hoy)
    t_sem,   u_sem,   c_sem   = calcular_totales_cat(ev_sem)
    t_hasta, u_hasta, c_hasta = calcular_totales_cat(ev_hasta)

    # ── Selector de fecha arriba a la derecha ────────────────────
    _, right = st.columns([3, 1])
    with right:
        rc1, rc2 = st.columns([1.2, 2])
        rc1.markdown("<div style='font-size:12px;color:#6B6B6B;padding-top:8px;text-align:right'>Proyectar hasta:</div>", unsafe_allow_html=True)
        with rc2:
            hasta_nueva = st.date_input(
                "f", value=st.session_state.hasta_fecha,
                min_value=hoy, key="inp_hasta_fecha",
                format="DD/MM/YYYY", label_visibility="collapsed"
            )
            if hasta_nueva != st.session_state.hasta_fecha:
                st.session_state.hasta_fecha = hasta_nueva
                st.rerun()

    fh        = st.session_state.hasta_fecha
    dias_diff = (fh - hoy).days

    # ── Tres columnas simétricas ────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<p class="dash-header">Hoy</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="dash-date">{DIAS_ES[hoy.weekday()]} {hoy.day} {MESES_ES[hoy.month]}</p>', unsafe_allow_html=True)
        st.metric(label="", value=f"${t_hoy:,.0f}", label_visibility="collapsed")
        if u_hoy > 0:
            st.metric(label="", value=f"U$S {u_hoy:,.0f}", label_visibility="collapsed")

    with col2:
        st.markdown('<p class="dash-header">Esta semana</p>', unsafe_allow_html=True)
        manana_str = f"{DIAS_ES[manana.weekday()]} {manana.day} — Dom {dom_sem.day} {MESES_ES[dom_sem.month]}"
        st.markdown(f'<p class="dash-date">{manana_str}</p>', unsafe_allow_html=True)
        st.metric(label="", value=f"${t_sem:,.0f}", label_visibility="collapsed")
        if u_sem > 0:
            st.metric(label="", value=f"U$S {u_sem:,.0f}", label_visibility="collapsed")

    with col3:
        st.markdown('<p class="dash-header">Próximas semanas</p>', unsafe_allow_html=True)
        hasta_str = f"{DIAS_ES[lunes_sig.weekday()]} {lunes_sig.day} {MESES_ES[lunes_sig.month]} — {DIAS_ES[fh.weekday()]} {fh.day} {MESES_ES[fh.month]}"
        st.markdown(f'<p class="dash-date">{hasta_str}</p>', unsafe_allow_html=True)
        st.metric(label="", value=f"${t_hasta:,.0f}", label_visibility="collapsed")
        if u_hasta > 0:
            st.metric(label="", value=f"U$S {u_hasta:,.0f}", label_visibility="collapsed")

    # ── Navegación semana ─────────────────────────────────────
    nav1, nav2, nav3, nav4 = st.columns([1, 4, 1, 2])
    if nav1.button("←", key="sem_prev"):
        st.session_state.sem_offset -= 1
        st.rerun()
    if nav3.button("→", key="sem_next"):
        st.session_state.sem_offset += 1
        st.rerun()
    if nav4.button("Hoy", key="sem_hoy"):
        st.session_state.sem_offset = 0
        st.rerun()

    if lunes_sem.month == domingo_sem.month:
        label_nav = f"{lunes_sem.day} – {domingo_sem.day} {MESES_ES[lunes_sem.month]} {lunes_sem.year}"
    else:
        label_nav = f"{lunes_sem.day} {MESES_ES[lunes_sem.month]} – {domingo_sem.day} {MESES_ES[domingo_sem.month]} {lunes_sem.year}"

    # Total de la semana navegada
    ev_nav_sem = [e for e in todos_egresos if lunes_sem <= e["fecha"] <= domingo_sem]
    total_nav_sem = sum(e["monto"] for e in ev_nav_sem)
    total_nav_usd = sum(e.get("monto_usd", 0) for e in ev_nav_sem)
    total_nav_str = f"${total_nav_sem:,.0f}" if total_nav_sem else ""
    if total_nav_usd > 0:
        total_nav_str += f" + U$S {total_nav_usd:,.0f}"

    nav2.markdown(
        f"<div style='padding-top:6px;font-size:18px;font-weight:500'>{label_nav}"
        f"{'  —  ' + total_nav_str if total_nav_str else ''}</div>",
        unsafe_allow_html=True
    )

    # ── Calendario semanal ─────────────────────────────────────
    DIAS_NOMBRES = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]
    cols_cal = st.columns(7)

    for i, (col, dia) in enumerate(zip(cols_cal, dias_semana)):
        es_hoy   = dia == hoy
        es_finde = i >= 5
        es_venc_dia = dia < hoy

        # Header
        color_header = "#D72B2B" if es_hoy else ("#AAAAAA" if es_finde else "#6B6B6B")
        borde_top = "border-top:2px solid #D72B2B;padding-top:4px;" if es_hoy else ""
        opacidad  = "opacity:0.5;" if es_finde else ""

        col.markdown(
            f'''<div style="{borde_top}{opacidad}text-align:center;margin-bottom:4px">
              <div style="font-size:11px;color:{color_header}">{DIAS_NOMBRES[i]}</div>
              <div style="font-size:18px;font-weight:500;color:{color_header};line-height:1.2">{dia.day}</div>
            </div>''',
            unsafe_allow_html=True
        )

        # Egresos del día
        evs_dia = [e for e in todos_egresos if e["fecha"] == dia]
        total_dia = 0
        total_dia_usd = 0

        for e in evs_dia:
            total_dia += e["monto"]
            total_dia_usd += e.get("monto_usd", 0)
            vencido = dia < hoy
            if vencido:
                c = CAT_COLORES["Vencido"]
            else:
                c = CAT_COLORES.get(e["cat"], CAT_COLORES["Financiero"])
            est_badge = " ⚠️" if e["est"] and not vencido else ""
            col.markdown(
                f'''<div style="background:{c["bg"]};color:{c["fg"]};border-left:3px solid {c["borde"]};
                  border-radius:5px;padding:5px 7px;margin-bottom:4px;font-size:14px">
                  <div style="font-weight:500;line-height:1.3">{e["desc"]}{est_badge}</div>
                  <div style="margin-top:2px;font-size:13px">{"${:,.0f} + U$S {:,.0f}".format(e["monto"], e["monto_usd"]) if e["monto"]>0 and e.get("monto_usd",0)>0 else "U$S {:,.0f}".format(e["monto_usd"]) if e["monto"]==0 and e.get("monto_usd",0)>0 else "${:,.0f}".format(e["monto"])}</div>
                </div>''',
                unsafe_allow_html=True
            )

        # Total diario
        if evs_dia:
            usd_str = f" + U$S {total_dia_usd:,.0f}" if total_dia_usd > 0 else ""
            col.markdown(
                f"<div style='font-size:13px;font-weight:500;color:#6B6B6B;"
                f"text-align:right;border-top:0.5px solid #E0E0E0;padding-top:3px;margin-top:2px'>"
                f"${total_dia:,.0f}{usd_str}</div>",
                unsafe_allow_html=True
            )

    # ── Plazos Fijos en Dashboard ────────────────────────────
    plazos_dash = db.get_plazos_fijos()
    hoy_pf = date.today()
    if plazos_dash:
        st.markdown("<div style='margin-top:20px;background:var(--color-background-secondary);border:0.5px solid var(--color-border-secondary);border-radius:var(--border-radius-lg);padding:14px 16px'>", unsafe_allow_html=True)
        st.markdown("<p class='dash-header' style='margin-bottom:10px'>Plazos Fijos</p>", unsafe_allow_html=True)
        # Ordenar por fecha de vencimiento
        plazos_ord = sorted([p for p in plazos_dash if p.get("vencimiento")],
                             key=lambda p: p["vencimiento"])
        cols_pf = st.columns(min(len(plazos_ord), 4))
        for ci, p in enumerate(plazos_ord):
            venc = date.fromisoformat(p["vencimiento"])
            dias_rest = (venc - hoy_pf).days
            if dias_rest < 0:
                color_venc = "#A32D2D"
                label_venc = f"Venció hace {abs(dias_rest)}d"
            elif dias_rest == 0:
                color_venc = "#D72B2B"
                label_venc = "Vence hoy"
            elif dias_rest <= 7:
                color_venc = "#BA7517"
                label_venc = f"Vence en {dias_rest}d"
            else:
                color_venc = "#3B6D11"
                label_venc = f"Vence {venc.strftime('%d/%m')}"
            with cols_pf[ci % 4]:
                st.markdown(
                    f"""<div style='background:var(--color-background-primary);border:0.5px solid var(--color-border-tertiary);
                    border-left:3px solid #639922;
                    border-radius:var(--border-radius-md);padding:10px 12px;margin-bottom:6px'>
                    <div style='font-size:12px;color:var(--color-text-secondary)'>{p['banco']}</div>
                    <div style='font-size:16px;font-weight:500;color:var(--color-text-primary)'>${p['monto']:,.0f}</div>
                    <div style='font-size:11px;color:{color_venc};margin-top:2px'>{label_venc}</div>
                    </div>""",
                    unsafe_allow_html=True
                )
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Leyenda ───────────────────────────────────────────────
    st.markdown("---")
    leyenda_html = " &nbsp;&nbsp; ".join([
        f'''<span style="display:inline-flex;align-items:center;gap:4px;font-size:11px;color:#6B6B6B">
          <span style="width:10px;height:10px;border-radius:2px;background:{v["bg"]};border-left:3px solid {v["borde"]};display:inline-block"></span>
          {k}</span>'''
        for k, v in CAT_COLORES.items()
    ])
    st.markdown(f"<div style='margin-top:4px'>{leyenda_html}</div>", unsafe_allow_html=True)




# ═══════════════════════════════════════════════════════════════
# TAB 2 — EGRESOS FINANCIEROS
# ═══════════════════════════════════════════════════════════════
with tab_fin:

    st.markdown('<div class="sec-title">Conceptos Financieros</div>', unsafe_allow_html=True)
    if not _es_admin:
        st.info("🔒 Solo lectura. Contactá al administrador para realizar cambios.")

    prestamos_conf = db.get_prestamos()
    fin_conf = db.get_financieros(solo_confirmados=True)
    tarjetas_vistas = {}
    for f in fin_conf:
        k = (f["organismo"], f["tipo"])
        if k not in tarjetas_vistas and not f.get("es_estimado"):
            tarjetas_vistas[k] = f

    # ── Encabezado unificado ───────────────────────────────────
    eh = st.columns([2,2,2,2,2,2,1])
    for col, txt in zip(eh, ["Concepto","Organismo","Tipo","Monto $","Monto U$S","Próx. Vencimiento / Última Cuota","Eliminar"]):
        col.markdown(f"<small style='color:#B0B0B0;font-size:11px'>{txt}</small>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:2px 0 6px'>", unsafe_allow_html=True)

    # ── Tarjetas ───────────────────────────────────────────────
    for (banco, tipo), f in tarjetas_vistas.items():
        try:
            fp = date.fromisoformat(f["fecha_pago_habil"])
            fecha_disp = fmt_fecha(fp)
        except Exception:
            fecha_disp = f.get("fecha_pago_habil","—")
        usd = f.get("monto_usd") or 0
        est = " ⚠️" if f.get("es_estimado") else ""
        tc = st.columns([2,2,2,2,2,2,1])
        tc[0].write("Tarjeta de Crédito")
        tc[1].write(banco)
        tc[2].write(f"{tipo}{est}")
        tc[3].write(f"${f['monto']:,.0f}")
        tc[4].write(f"U$S {usd:,.2f}" if usd else "—")
        tc[5].write(fecha_disp)
        if tc[6].button("🗑️", key=f"del_tar_{f['id']}", help="Eliminar tarjeta"):
            db.delete_financiero(f["id"])
            st.rerun()

    # ── Préstamos y Planes ─────────────────────────────────────
    cambios_prest = {}
    for p in prestamos_conf:
        pc = st.columns([2,2,2,2,2,2,1])
        pc[0].write("Préstamo" if p["subtipo"]=="prestamo" else "Plan de Pagos")
        pc[1].write(p["organismo"])
        pc[2].write(p["concepto"])
        nuevo_monto_p = pc[3].number_input("m", value=float(p["monto"]), min_value=0.0, step=10_000.0,
                           format="%.0f", key=f"pm_{p['id']}", label_visibility="collapsed")
        pc[4].write("—")
        try:
            fecha_actual = date.fromisoformat(p["fecha_ultima_cuota"])
        except Exception:
            fecha_actual = date(2030,12,31)
        nueva_fecha = pc[5].date_input("f", value=fecha_actual,
                           key=f"pf_{p['id']}", label_visibility="collapsed",
                           format="DD/MM/YYYY")
        if pc[6].button("🗑️", key=f"del_p_{p['id']}", help="Eliminar"):
            db.delete_prestamo(p["id"])
            st.rerun()
        if nuevo_monto_p != p["monto"] or nueva_fecha.isoformat() != p["fecha_ultima_cuota"]:
            cambios_prest[p["id"]] = {"p": p, "monto": nuevo_monto_p, "fecha": nueva_fecha.isoformat()}

    if cambios_prest:
        if st.button("💾 Guardar cambios", key="btn_gp"):
            for id_, datos in cambios_prest.items():
                p = datos["p"]
                db.update_prestamo(id_, p["concepto"], p["organismo"],
                                   datos["monto"], p["regla"],
                                   datos["fecha"], bool(p["activo"]))
            cached_proyeccion_prestamos.clear()
            st.success("✅ Guardado.")
            st.rerun()

    st.markdown("<small style='color:#B0B0B0;font-size:11px'>📌 Para préstamos y planes de pago, la última columna indica la fecha de la <b>última cuota</b>.</small>", unsafe_allow_html=True)
    st.markdown("---")

    # ── Agregar nuevo préstamo/plan ────────────────────────────
    with st.expander("➕ Agregar préstamo o plan de pago"):
        nc1, nc2 = st.columns(2)
        with nc1:
            n_subtipo   = st.selectbox("Concepto", ["prestamo","plan_de_pago"], key="nf_subtipo",
                                        format_func=lambda x: "Préstamo" if x=="prestamo" else "Plan de Pagos")
            n_organismo = st.text_input("Organismo", key="nf_org")
            n_tipo      = st.text_input("Tipo", key="nf_tipo", placeholder="Ej: Galpón 1")
        with nc2:
            n_monto  = st.number_input("Monto mensual ($)", min_value=0.0, step=10_000.0, key="nf_monto")
            n_regla  = st.selectbox("Día de pago", bl.REGLAS_DISPONIBLES, key="nf_regla",
                                    format_func=lambda x: bl.REGLA_LABEL.get(x, x))
            n_ultima = st.date_input("Fecha última cuota", min_value=date.today(), key="nf_ultima")
        if st.button("💾 Guardar", key="btn_save_fin"):
            if n_tipo and n_monto > 0:
                db.insert_prestamo(n_tipo, n_organismo, n_subtipo, n_monto, n_regla, n_ultima.isoformat())
                st.success(f"✅ {n_tipo} guardado.")
                st.rerun()
            else:
                st.error("Completá tipo y monto.")

    st.markdown("---")

    # ── Cargar resúmenes mensuales ────────────────────────────
    st.markdown('<div class="sec-title">Cargar Resúmenes Bancarios (PDF)</div>', unsafe_allow_html=True)
    if True:
        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0
        if "confirmados_tanda" not in st.session_state:
            st.session_state.confirmados_tanda = set()

        archivos = st.file_uploader(
            "Arrastrá o seleccioná hasta 4 PDFs", type=["pdf"],
            accept_multiple_files=True,
            key=f"pdf_uploader_{st.session_state.uploader_key}",
        )
        nombres_actuales = tuple(sorted(f.name for f in archivos)) if archivos else ()
        if st.session_state.get("nombres_uploader") != nombres_actuales:
            st.session_state.nombres_uploader = nombres_actuales
            st.session_state.confirmados_tanda = set()

        if archivos:
            if len(archivos) > 4:
                archivos = archivos[:4]

            @st.cache_data(show_spinner=False)
            def procesar_pdfs_cached(archivos_bytes):
                return pdf_ext.analizar_multiples_pdfs(list(archivos_bytes))

            with st.spinner("Procesando PDFs..."):
                pares     = tuple((f.name, f.read()) for f in archivos)
                extraidos = procesar_pdfs_cached(pares)

            # Usar banco+tipo como clave para detectar duplicados, no el nombre del archivo
            financieros_actuales = db.get_financieros()
            bancos_tipo_guardados = {(r["banco"], r["tipo"]) for r in financieros_actuales if not r.get("es_estimado")}
            confirmados_banco_tipo = st.session_state.get("confirmados_banco_tipo", set())
            pdfs_a_ignorar_nombre = st.session_state.confirmados_tanda
            pendientes = [r for r in extraidos
                         if (r.get("banco",""), r.get("tipo","")) not in confirmados_banco_tipo
                         and r["origen_pdf"] not in pdfs_a_ignorar_nombre]

            if len(st.session_state.confirmados_tanda) > 0 and not pendientes:
                st.success("✅ Todos los PDFs guardados.")
                st.session_state.confirmados_tanda = set()
                st.session_state.uploader_key += 1
                st.rerun()

            if not pendientes and not st.session_state.confirmados_tanda:
                st.success("✅ Ya guardados en el historial.")
            elif pendientes:
                if len(st.session_state.confirmados_tanda) > 0:
                    st.info(f"✅ {len(st.session_state.confirmados_tanda)} de {len(extraidos)} guardados.")

            for r in pendientes:
                if r.get("error"):
                    st.error(f"❌ {r['origen_pdf']}: {r['error']}")
                    continue
                k = r["origen_pdf"].replace(".", "_").replace(" ", "_").replace("-", "_")
                conf_icon = "✅" if r["confianza"]=="alta" else "⚠️" if r["confianza"]=="media" else "❌"
                with st.expander(f"📄 {r['origen_pdf']}  |  {conf_icon} {r['confianza'].upper()}", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        banco = st.text_input("Banco", value=r["banco"], key=f"banco_{k}")
                        tipo  = st.text_input("Tipo", value=r["tipo"], key=f"tipo_{k}")
                        fecha_venc = st.date_input("Fecha vencimiento",
                                                   value=r["fecha_vencimiento"] or date.today(), key=f"fvenc_{k}")
                    with col2:
                        monto     = st.number_input("Monto ($)", value=float(r["monto"] or 0),
                                                    min_value=0.0, step=1000.0, key=f"monto_{k}")
                        monto_usd = st.number_input("Monto (U$S)", value=float(r["monto_usd"] or 0),
                                                    min_value=0.0, step=1.0, key=f"musd_{k}")
                        notas = st.text_input("Notas", key=f"notas_{k}", placeholder="")
                    fecha_habil = bl.siguiente_dia_habil(fecha_venc) if fecha_venc else None
                    if fecha_habil and fecha_habil != fecha_venc:
                        st.info(f"📅 Ajustado al día hábil: **{fmt_fecha(fecha_habil)}**")
                    if r.get("fecha_prox_venc"):
                        fp  = r["fecha_prox_venc"]
                        fph = r.get("fecha_prox_habil") or bl.siguiente_dia_habil(fp)
                        st.info(f"📅 Próximo: {fmt_fecha(fp)}" + (f" → hábil: {fmt_fecha(fph)}" if fph!=fp else "") + " — se guardará como estimado.")
                    if st.button(f"✅ Confirmar — {banco}", key=f"confirm_{k}"):
                        if monto > 0 and fecha_venc:
                            # Eliminar registro anterior confirmado del mismo banco+tipo
                            db.reemplazar_confirmado(banco, tipo)
                            db.reemplazar_estimado(banco, tipo, monto, monto_usd,
                                                   fecha_venc.isoformat(),
                                                   fecha_habil.isoformat() if fecha_habil else fecha_venc.isoformat(),
                                                   r["origen_pdf"])
                            if "confirmados_banco_tipo" not in st.session_state:
                                st.session_state.confirmados_banco_tipo = set()
                            st.session_state.confirmados_banco_tipo.add((banco, tipo))
                            new_id = db.insert_financiero(
                                banco, tipo, monto, monto_usd, fecha_venc.isoformat(),
                                fecha_habil.isoformat() if fecha_habil else fecha_venc.isoformat(),
                                r["origen_pdf"], notas, 0
                            )
                            db.confirmar_financiero(new_id)
                            if r.get("fecha_prox_venc"):
                                fp  = r["fecha_prox_venc"]
                                fph = r.get("fecha_prox_habil") or bl.siguiente_dia_habil(fp)
                                est_id = db.insert_financiero(
                                    banco, tipo, monto, 0.0, fp.isoformat(), fph.isoformat(),
                                    f"Estimado basado en {r['origen_pdf']}", "Monto estimado", 1
                                )
                                db.confirmar_financiero(est_id)
                            st.session_state.confirmados_tanda.add(r["origen_pdf"])
                            st.success(f"✅ Guardado (ID #{new_id})" + (" + estimado" if r.get("fecha_prox_venc") else ""))
                            st.rerun()
                        else:
                            st.error("Completá monto y fecha.")

with tab_imp:

    st.markdown('<div class="sec-title">Conceptos Impositivos</div>', unsafe_allow_html=True)

    impositivos_db = db.get_impositivos()

    # ── Encabezado ──────────────────────────────────────────────
    ei = st.columns([4, 2, 2, 1])
    for col, txt in zip(ei, ["Concepto","Monto ($)","Regla","Eliminar"]):
        col.markdown(f"<small style='color:#B0B0B0;font-size:11px'>{txt}</small>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:2px 0 6px'>", unsafe_allow_html=True)

    from datetime import date as _date
    _hoy_imp = _date.today()
    _mes_dev = (_hoy_imp.month - 2) % 12 + 1
    _anio_dev = _hoy_imp.year - (1 if _hoy_imp.month == 1 else 0)
    _ARCA_CONCEPTOS = {"Autónomos", "Empleada Doméstica", "Monotributo"}
    _arca_montos = {
        "Autónomos": bl.get_monto_autonomos(_anio_dev, _mes_dev),
        "Empleada Doméstica": bl.get_monto_empleada(_anio_dev, _mes_dev),
        "Monotributo": bl.get_monto_monotributo(_hoy_imp.year, _hoy_imp.month),
    }

    for reg in impositivos_db:
        c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
        c1.write(reg["concepto"])
        es_arca = reg["concepto"] in _ARCA_CONCEPTOS
        monto_arca = _arca_montos.get(reg["concepto"], 0)
        monto_display = float(reg["monto"]) if reg["monto"] > 0 else monto_arca
        if es_arca and reg["monto"] == 0:
            c2.markdown(f"<div style='font-size:16px;padding-top:6px'>${monto_arca:,.0f} <small style='color:#B0B0B0;font-size:11px'>(ARCA)</small></div>", unsafe_allow_html=True)
            nuevo_monto = reg["monto"]
        else:
            nuevo_monto = c2.number_input(
                "m", value=float(reg["monto"]), min_value=0.0, step=10_000.0,
                format="%.0f", key=f"imp_m_{reg['id']}", label_visibility="collapsed"
            )
        dia_actual_imp = int(reg["regla"][1:]) if reg["regla"].startswith("d") and reg["regla"][1:].isdigit() else 10
        nuevo_dia_imp = c3.number_input(
            "d", value=dia_actual_imp, min_value=1, max_value=31,
            key=f"imp_r_{reg['id']}", label_visibility="collapsed"
        )
        nueva_regla = f"d{int(nuevo_dia_imp):02d}" if nuevo_dia_imp != 1 else "d01"
        if c4.button("🗑️", key=f"del_imp_{reg['id']}", help="Eliminar"):
            db.delete_impositivo(reg["id"])
            st.rerun()

        if nuevo_monto != reg["monto"] or nueva_regla != reg["regla"]:
            db.update_impositivo(id_=reg["id"], monto=nuevo_monto, regla=nueva_regla, activo=reg["activo"])

    st.markdown("---")

    with st.expander("➕ Agregar concepto impositivo"):
        ai1, ai2, ai3, ai4 = st.columns(4)
        nuevo_concepto_imp = ai1.text_input("Concepto", key="new_imp_concepto")
        nuevo_org_imp      = ai2.text_input("Organismo", value="ARCA", key="new_imp_org")
        nuevo_monto_imp    = ai3.number_input("Monto ($)", min_value=0.0, step=10_000.0, key="new_imp_monto")
        nuevo_dia_imp_new = ai4.number_input("Día", value=10, min_value=1, max_value=31, key="new_imp_dia")
        if st.button("💾 Agregar", key="btn_add_imp"):
            if nuevo_concepto_imp:
                nueva_regla_imp = f"d{int(nuevo_dia_imp_new):02d}" if nuevo_dia_imp_new != 1 else "d01"
                db.insert_impositivo(nuevo_concepto_imp, nuevo_org_imp, nuevo_monto_imp, nueva_regla_imp)
                st.success(f"✅ {nuevo_concepto_imp} agregado.")
                st.rerun()



with tab_lab:

    st.markdown('<div class="sec-title">Conceptos Laborales</div>', unsafe_allow_html=True)
    if not _es_admin:
        st.info("🔒 Solo lectura. Contactá al administrador para realizar cambios.")

    laborales = db.get_laborales()

    # ── Tabla editable fila por fila ────────────────────────────
    # Encabezados
    h1, h2, h3, h4 = st.columns([4, 2, 2, 1])
    for col, txt in zip([h1,h2,h3,h4], ["Concepto","Monto ($)","Regla","Eliminar"]):
        col.markdown(f"<small style='color:#B0B0B0;font-size:11px'>{txt}</small>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:2px 0 6px'>", unsafe_allow_html=True)

    cambios_lab = {}
    for reg in laborales:
        c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
        c1.write(reg["concepto"])
        nuevo_monto = c2.number_input(
            "m", value=float(reg["monto"]), min_value=0.0, step=500_000.0,
            format="%.0f", key=f"lab_m_{reg['id']}", label_visibility="collapsed"
        )
        reglas_lab = bl.REGLAS_DISPONIBLES + ["aguinaldo","penultimo_habil","arca"]
        reglas_lab = list(dict.fromkeys(reglas_lab))
        idx_regla = reglas_lab.index(reg["regla"]) if reg["regla"] in reglas_lab else 0
        nueva_regla = c3.selectbox(
            "r", reglas_lab, index=idx_regla,
            key=f"lab_r_{reg['id']}", label_visibility="collapsed",
            format_func=lambda x: bl.REGLA_LABEL.get(x, x)
        )
        if c4.button("🗑️", key=f"del_lab_{reg['id']}", help="Eliminar"):
            db.delete_laboral(reg["id"])
            st.rerun()
        if nuevo_monto != reg["monto"] or nueva_regla != reg["regla"]:
            cambios_lab[reg["id"]] = {"monto": nuevo_monto, "regla": nueva_regla}

    if cambios_lab:
        if st.button("💾 Guardar cambios"):
            for id_, datos in cambios_lab.items():
                db.update_laboral(id_, datos["monto"], datos["regla"], True)
            cached_proyeccion_laborales.clear()
            st.success("✅ Cambios guardados.")
            st.rerun()

    # ── Recalcular aguinaldo ────────────────────────────────────
    n_filas = len(laborales)
    _, col_recalc = st.columns([4, 1])
    if col_recalc.button("🔄", help="Recalcular aguinaldo: id2 + (id3 × 0.5)", key="btn_recalc"):
        labs_dict = {r["id"]: r["monto"] for r in laborales}
        monto_id2 = labs_dict.get(2, 0)
        monto_id3 = labs_dict.get(3, 0)
        aguinaldo_calc = monto_id2 + (monto_id3 * 0.5)
        id_aguinaldo = next((r["id"] for r in laborales if r["regla"] == "aguinaldo"), None)
        if id_aguinaldo:
            db.update_laboral(id_=id_aguinaldo, monto=aguinaldo_calc, activo=True)
            st.success(f"✅ Aguinaldo recalculado: ${aguinaldo_calc:,.0f}")
            st.rerun()

    st.markdown("---")

    # ── Agregar nuevo concepto laboral ──────────────────────────
    with st.expander("➕ Añadir concepto laboral"):
        al1, al2, al3 = st.columns(3)
        nuevo_concepto_lab = al1.text_input("Concepto", key="new_lab_concepto")
        nuevo_monto_lab    = al2.number_input("Monto ($)", min_value=0.0, step=100_000.0, key="new_lab_monto")
        nueva_regla_lab    = al3.selectbox("Regla", bl.REGLAS_DISPONIBLES + ["aguinaldo","penultimo_habil","arca"],
                                            key="new_lab_regla",
                                            format_func=lambda x: bl.REGLA_LABEL.get(x, x))
        if st.button("💾 Agregar", key="btn_add_lab"):
            if nuevo_concepto_lab:
                db.insert_laboral(nuevo_concepto_lab, nuevo_monto_lab, nueva_regla_lab)
                st.success(f"✅ {nuevo_concepto_lab} agregado.")
                st.rerun()




# ═══════════════════════════════════════════════════════════════
# TAB 5 — COMERCIALES (Proveedores de Servicios)
# ═══════════════════════════════════════════════════════════════
with tab_com:

    st.markdown('<div class="sec-title">Proveedores de Servicios</div>', unsafe_allow_html=True)
    if not _es_admin:
        st.info("🔒 Solo lectura. Contactá al administrador para realizar cambios.")

    proveedores_db = db.get_proveedores()

    # ── Encabezado ──────────────────────────────────────────────
    eh = st.columns([1, 3, 2, 2, 2, 2, 1])
    for col, txt in zip(eh, ["Cód", "Proveedor", "Categoría", "Monto ($)", "Día 1", "Día 2", "Eliminar"]):
        col.markdown(f"<small style='color:#B0B0B0;font-size:11px'>{txt}</small>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:2px 0 6px'>", unsafe_allow_html=True)

    cambios_prov = {}
    for p in proveedores_db:
        pc = st.columns([1, 3, 2, 2, 2, 2, 1])
        pc[0].write(p["codigo"])
        pc[1].write(p["nombre"])
        nueva_cat_p = pc[2].text_input(
            "c", value=p.get("categoria",""), key=f"prov_c_{p['id']}", label_visibility="collapsed",
            placeholder="ej: Alquiler"
        )
        nuevo_monto_p = pc[3].number_input(
            "m", value=float(p["monto"]), min_value=0.0, step=10_000.0,
            format="%.0f", key=f"prov_m_{p['id']}", label_visibility="collapsed"
        )
        dia1_actual = int(p["regla"][1:]) if p["regla"].startswith("d") and p["regla"][1:].isdigit() else 10
        nuevo_dia1_p = pc[4].number_input(
            "d1", value=dia1_actual, min_value=1, max_value=31,
            key=f"prov_d1_{p['id']}", label_visibility="collapsed"
        )
        nueva_regla_p = f"d{int(nuevo_dia1_p):02d}" if nuevo_dia1_p != 1 else "d01"
        dia2_actual = int(p["regla2"][1:]) if p.get("regla2","").startswith("d") and p["regla2"][1:].isdigit() else 0
        nuevo_dia2_p = pc[5].number_input(
            "d2", value=dia2_actual, min_value=0, max_value=31,
            key=f"prov_d2_{p['id']}", label_visibility="collapsed",
            help="0 = sin segundo pago"
        )
        nueva_regla2_p = f"d{int(nuevo_dia2_p):02d}" if nuevo_dia2_p > 1 else ("d01" if nuevo_dia2_p == 1 else "")
        if pc[6].button("🗑️", key=f"del_prov_{p['id']}", help="Eliminar"):
            db.delete_proveedor(p["id"])
            st.rerun()
        if (nuevo_monto_p != p["monto"] or nueva_regla_p != p["regla"] or
                nueva_cat_p != p.get("categoria","") or nueva_regla2_p != p.get("regla2","")):
            cambios_prov[p["id"]] = {"categoria": nueva_cat_p, "monto": nuevo_monto_p,
                                      "regla": nueva_regla_p, "regla2": nueva_regla2_p}

    if cambios_prov:
        if st.button("💾 Guardar cambios", key="btn_save_prov"):
            for id_, datos in cambios_prov.items():
                db.update_proveedor(id_=id_, categoria=datos["categoria"], monto=datos["monto"], regla=datos["regla"], regla2=datos["regla2"], activo=True)
            cached_proyeccion_comercial.clear()
            st.success("✅ Cambios guardados.")
            st.rerun()

    st.markdown("---")

    # ── Agregar nuevo proveedor ─────────────────────────────────
    with st.expander("➕ Agregar proveedor"):
        ap1, ap2, ap3, ap4, ap5, ap6 = st.columns([1, 3, 2, 2, 2, 2])
        n_codigo  = ap1.text_input("Cód", key="new_prov_cod", placeholder="P001")
        n_nombre  = ap2.text_input("Proveedor", key="new_prov_nombre")
        n_cat_p   = ap3.text_input("Categoría", key="new_prov_cat", placeholder="ej: Alquiler")
        n_monto_p = ap4.number_input("Monto ($)", min_value=0.0, step=10_000.0, key="new_prov_monto")
        n_dia1_p = ap5.number_input("Día 1", value=10, min_value=1, max_value=31, key="new_prov_dia1")
        n_dia2_p = ap6.number_input("Día 2", value=0, min_value=0, max_value=31, key="new_prov_dia2",
                                     help="0 = sin segundo pago")
        if st.button("💾 Agregar", key="btn_add_prov"):
            if n_nombre:
                n_regla_p  = f"d{int(n_dia1_p):02d}" if n_dia1_p != 1 else "d01"
                n_regla2_p = f"d{int(n_dia2_p):02d}" if n_dia2_p > 1 else ("d01" if n_dia2_p == 1 else "")
                db.insert_proveedor(n_codigo, n_nombre.strip().title(), n_cat_p, n_monto_p, n_regla_p, n_regla2_p)
                cached_proyeccion_comercial.clear()
                st.success(f"✅ {n_nombre} agregado.")
                st.rerun()
            else:
                st.error("Completá el nombre del proveedor.")


# ═══════════════════════════════════════════════════════════════
# TAB 6 — ADUANERO
# ═══════════════════════════════════════════════════════════════
with tab_adu:

    st.markdown('<div class="sec-title">Compromisos Aduaneros</div>', unsafe_allow_html=True)

    aduanero_db_raw = db.get_aduanero()
    # Filtrar: ocultar los vencidos hace más de 10 días
    _hoy_adu = date.today()
    aduanero_db = [r for r in aduanero_db_raw
                   if not r.get("vencimiento") or
                   (date.fromisoformat(r["vencimiento"]) >= _hoy_adu - timedelta(days=10))]

    # ── Encabezado ──────────────────────────────────────────────
    eh = st.columns([1, 3, 2, 2, 1])
    for col, txt in zip(eh, ["Cód", "Proveedor", "Monto U$S", "Vencimiento", "Eliminar"]):
        col.markdown(f"<small style='color:#B0B0B0;font-size:11px'>{txt}</small>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:2px 0 6px'>", unsafe_allow_html=True)

    cambios_adu = {}
    for reg in aduanero_db:
        ac = st.columns([1, 3, 2, 2, 1])
        ac[0].write(reg["codigo"])
        ac[1].write(reg["proveedor"])
        nuevo_monto_adu = ac[2].number_input(
            "u", value=float(reg["monto_usd"]), min_value=0.0, step=100.0,
            format="%.2f", key=f"adu_m_{reg['id']}", label_visibility="collapsed"
        )
        try:
            venc_actual = date.fromisoformat(reg["vencimiento"]) if reg["vencimiento"] else date.today()
        except Exception:
            venc_actual = date.today()
        nuevo_venc_adu = ac[3].date_input(
            "v", value=venc_actual, key=f"adu_v_{reg['id']}",
            format="DD/MM/YYYY", label_visibility="collapsed"
        )
        if ac[4].button("🗑️", key=f"del_adu_{reg['id']}", help="Eliminar"):
            db.delete_aduanero(reg["id"])
            st.rerun()
        if nuevo_monto_adu != reg["monto_usd"] or nuevo_venc_adu.isoformat() != reg["vencimiento"]:
            cambios_adu[reg["id"]] = {"monto_usd": nuevo_monto_adu, "vencimiento": nuevo_venc_adu.isoformat()}

    if cambios_adu:
        if st.button("💾 Guardar cambios", key="btn_save_adu"):
            for id_, datos in cambios_adu.items():
                db.update_aduanero(id_=id_, monto_usd=datos["monto_usd"],
                                   vencimiento=datos["vencimiento"], activo=True)
            st.success("✅ Cambios guardados.")
            st.rerun()

    st.markdown("---")

    with st.expander("➕ Agregar egreso aduanero"):
        aa1, aa2, aa3, aa4 = st.columns([1, 3, 2, 2])
        n_cod_adu   = aa1.text_input("Cód", key="new_adu_cod", placeholder="A001")
        n_prov_adu  = aa2.text_input("Proveedor", key="new_adu_prov")
        n_monto_adu = aa3.number_input("Monto U$S", min_value=0.0, step=100.0, format="%.2f", key="new_adu_monto")
        n_venc_adu  = aa4.date_input("Vencimiento", value=date.today(), key="new_adu_venc", format="DD/MM/YYYY")
        if st.button("💾 Agregar", key="btn_add_adu"):
            if n_prov_adu:
                db.insert_aduanero(n_cod_adu, n_prov_adu.strip().title(), n_monto_adu, n_venc_adu.isoformat())
                st.success(f"✅ {n_prov_adu} agregado.")
                st.rerun()
            else:
                st.error("Completá el nombre del proveedor.")


# ═══════════════════════════════════════════════════════════════
# TAB USUARIOS (solo admin)
# ═══════════════════════════════════════════════════════════════
if _es_admin and tab_usr is not None:
    with tab_usr:
        st.markdown('<div class="sec-title">Gestión de Usuarios</div>', unsafe_allow_html=True)

        usuarios_db = db.get_usuarios()

        # Encabezado
        eh = st.columns([2, 2, 1, 1, 1])
        for col, txt in zip(eh, ["Usuario", "Nombre", "Rol", "Activo", "Eliminar"]):
            col.markdown(f"<small style='color:#B0B0B0;font-size:11px'>{txt}</small>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:2px 0 6px'>", unsafe_allow_html=True)

        for u in usuarios_db:
            uc = st.columns([2, 2, 1, 1, 1])
            uc[0].write(u["username"])
            uc[1].write(u["nombre"] or "—")
            uc[2].write(u["rol"])
            activo_val = bool(u["activo"])
            nuevo_activo = uc[3].checkbox("", value=activo_val, key=f"usr_act_{u['id']}", label_visibility="collapsed")
            if nuevo_activo != activo_val:
                db.update_usuario_activo(u["id"], nuevo_activo)
                st.rerun()
            if u["rol"] != "admin":
                if uc[4].button("🗑️", key=f"del_usr_{u['id']}", help="Eliminar"):
                    db.delete_usuario(u["id"])
                    st.rerun()

        st.markdown("---")

        # Cambiar contraseña
        with st.expander("🔑 Cambiar contraseña"):
            cp1, cp2, cp3 = st.columns(3)
            usr_sel = cp1.selectbox("Usuario", [u["username"] for u in usuarios_db], key="cp_usr")
            new_pwd = cp2.text_input("Nueva contraseña", type="password", key="cp_pwd")
            if cp3.button("Guardar", key="btn_cp"):
                if new_pwd:
                    uid = next(u["id"] for u in usuarios_db if u["username"] == usr_sel)
                    db.update_usuario_password(uid, new_pwd)
                    st.success("✅ Contraseña actualizada.")

        st.markdown("---")

        # Agregar usuario
        with st.expander("➕ Agregar usuario"):
            nu1, nu2, nu3, nu4 = st.columns(4)
            n_usr  = nu1.text_input("Usuario", key="new_usr_name")
            n_nom  = nu2.text_input("Nombre", key="new_usr_nom")
            n_rol  = nu3.selectbox("Rol", ["usuario", "admin"], key="new_usr_rol")
            n_pwd  = nu4.text_input("Contraseña", type="password", key="new_usr_pwd")
            if st.button("💾 Agregar usuario", key="btn_add_usr"):
                if n_usr and n_pwd:
                    try:
                        db.insert_usuario(n_usr, n_pwd, n_rol, n_nom)
                        st.success(f"✅ Usuario '{n_usr}' creado.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                else:
                    st.error("Completá usuario y contraseña.")


# ═══════════════════════════════════════════════════════════════
# TAB INGRESOS — Plazos Fijos
# ═══════════════════════════════════════════════════════════════
with tab_ing:

    st.markdown('<div class="sec-title">Plazos Fijos</div>', unsafe_allow_html=True)

    plazos_db = db.get_plazos_fijos()

    # Encabezado
    eh = st.columns([3, 2, 2, 1])
    for col, txt in zip(eh, ["Banco", "Monto ($)", "Vencimiento", "Eliminar"]):
        col.markdown(f"<small style='color:#B0B0B0;font-size:11px'>{txt}</small>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:2px 0 6px'>", unsafe_allow_html=True)

    cambios_pf = {}
    for p in plazos_db:
        pc = st.columns([3, 2, 2, 1])
        nuevo_banco_pf = pc[0].text_input(
            "b", value=p["banco"], key=f"pf_b_{p['id']}", label_visibility="collapsed"
        )
        nuevo_monto_pf = pc[1].number_input(
            "m", value=float(p["monto"]), min_value=0.0, step=100_000.0,
            format="%.0f", key=f"pf_m_{p['id']}", label_visibility="collapsed"
        )
        try:
            venc_pf = date.fromisoformat(p["vencimiento"]) if p["vencimiento"] else date.today()
        except Exception:
            venc_pf = date.today()
        nuevo_venc_pf = pc[2].date_input(
            "v", value=venc_pf, key=f"pf_v_{p['id']}",
            format="DD/MM/YYYY", label_visibility="collapsed"
        )
        if pc[3].button("🗑️", key=f"del_pf_{p['id']}", help="Eliminar"):
            db.delete_plazo_fijo(p["id"])
            st.rerun()

        if (nuevo_banco_pf != p["banco"] or nuevo_monto_pf != p["monto"] or
                nuevo_venc_pf.isoformat() != p["vencimiento"]):
            cambios_pf[p["id"]] = {
                "banco": nuevo_banco_pf, "monto": nuevo_monto_pf,
                "vencimiento": nuevo_venc_pf.isoformat()
            }

    if cambios_pf:
        if st.button("💾 Guardar cambios", key="btn_save_pf"):
            for id_, datos in cambios_pf.items():
                db.update_plazo_fijo(id_=id_, banco=datos["banco"], monto=datos["monto"],
                                     vencimiento=datos["vencimiento"], notas="")
            st.success("✅ Cambios guardados.")
            st.rerun()

    st.markdown("---")

    with st.expander("➕ Agregar plazo fijo"):
        ap1, ap2, ap3 = st.columns([3, 2, 2])
        n_banco_pf = ap1.text_input("Banco", key="new_pf_banco")
        n_monto_pf = ap2.number_input("Monto ($)", min_value=0.0, step=100_000.0, format="%.0f", key="new_pf_monto")
        n_venc_pf  = ap3.date_input("Vencimiento", value=date.today(), key="new_pf_venc", format="DD/MM/YYYY")
        if st.button("💾 Agregar", key="btn_add_pf"):
            if n_banco_pf and n_monto_pf > 0:
                db.insert_plazo_fijo(n_banco_pf.strip().title(), n_monto_pf,
                                     n_venc_pf.isoformat(), "")
                st.success(f"✅ Plazo fijo {n_banco_pf} agregado.")
                st.rerun()
            else:
                st.error("Completá banco y monto.")
