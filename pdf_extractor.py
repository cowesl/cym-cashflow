"""
CYM Materiales SA — Cash Flow
Módulo: Extracción de Datos de PDFs Bancarios
Versión: 4.0

Bancos soportados: BBVA, Banco Credicoop (Visa y Cabal), Banco Santander Río
Extrae: banco, tipo, monto ARS, monto USD, fecha vencimiento actual, próximo vencimiento
"""

import re
import io
from datetime import date, timedelta
from typing import Optional

try:
    import pdfplumber
    PDF_ENGINE = "pdfplumber"
except ImportError:
    pdfplumber = None
    PDF_ENGINE = None

try:
    import PyPDF2
    if PDF_ENGINE is None:
        PDF_ENGINE = "PyPDF2"
except ImportError:
    PyPDF2 = None

if PDF_ENGINE is None:
    raise ImportError("Instalar con: pip install pdfplumber")


# ── Feriados Argentina 2025-2026 ───────────────────────────────────────────
FERIADOS_AR = {
    date(2025, 1, 1), date(2025, 3, 3), date(2025, 3, 4),
    date(2025, 4, 2), date(2025, 4, 18), date(2025, 5, 1),
    date(2025, 5, 25), date(2025, 6, 16), date(2025, 6, 20),
    date(2025, 7, 9), date(2025, 8, 17), date(2025, 10, 12),
    date(2025, 11, 17), date(2025, 11, 20), date(2025, 12, 8), date(2025, 12, 25),
    date(2026, 1, 1), date(2026, 2, 16), date(2026, 2, 17),
    date(2026, 4, 2), date(2026, 4, 3), date(2026, 5, 1),
    date(2026, 5, 25), date(2026, 6, 15), date(2026, 6, 20),
    date(2026, 7, 9), date(2026, 8, 17), date(2026, 10, 12),
    date(2026, 11, 20), date(2026, 12, 8), date(2026, 12, 25),
}

MESES_ES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
    "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def siguiente_dia_habil(d: date) -> date:
    while d.weekday() >= 5 or d in FERIADOS_AR:
        d += timedelta(days=1)
    return d


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACCIÓN DE TEXTO — pág 1 + pág 2 + última
# ─────────────────────────────────────────────────────────────────────────────

def extraer_texto_pdf(file_bytes: bytes) -> str:
    texto = ""
    if PDF_ENGINE == "pdfplumber":
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            paginas = list(pdf.pages)
            n = len(paginas)
            indices = sorted(set([0, min(1, n - 1), n - 1]))
            for i in indices:
                t = paginas[i].extract_text()
                if t:
                    texto += t + "\n"
    else:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        paginas = reader.pages
        n = len(paginas)
        indices = sorted(set([0, min(1, n - 1), n - 1]))
        for i in indices:
            t = paginas[i].extract_text()
            if t:
                texto += t + "\n"
    return texto


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar_monto(raw: str) -> Optional[float]:
    raw = raw.strip()
    if "," in raw and raw.rfind(",") > raw.rfind("."):
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", "")
    try:
        v = float(raw)
        return v if v >= 100 else None
    except ValueError:
        return None


def _fecha_desde_abrev(dia: str, mes_str: str, anio: str) -> Optional[date]:
    mes = MESES_ES.get(mes_str.lower()[:3])
    if not mes:
        return None
    a = int(anio)
    if a < 100:
        a += 2000
    try:
        return date(a, mes, int(dia))
    except ValueError:
        return None


def _fecha_desde_ddmmaaaa(s: str) -> Optional[date]:
    """Parsea DD/MM/AAAA o DD/MM/AA"""
    m = re.match(r"(\d{1,2})[/\-](\d{2})[/\-](\d{2,4})$", s.strip())
    if m:
        a = int(m.group(3))
        if a < 100:
            a += 2000
        try:
            return date(a, int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# DETECCIÓN DE BANCO Y TIPO
# ─────────────────────────────────────────────────────────────────────────────

def _detectar_banco(texto: str) -> str:
    if (re.search(r"visa\s+business", texto, re.I) and
            re.search(r"resumen\s+con\s+vencimiento", texto, re.I)):
        return "BBVA"
    if re.search(r"credicoop", texto, re.I):
        return "Banco Credicoop"
    if re.search(r"santander", texto, re.I):
        return "Banco Santander"
    for patron, nombre in [
        (r"banco\s+galicia|galicia", "Banco Galicia"),
        (r"banco\s+macro|\bmacro\b", "Banco Macro"),
        (r"supervielle", "Supervielle"),
        (r"ita[uú]", "Itaú"),
        (r"\bhsbc\b", "HSBC"),
        (r"\bicbc\b", "ICBC"),
    ]:
        if re.search(patron, texto, re.I):
            return nombre
    return "Banco Desconocido"


def _detectar_tipo(texto: str, banco: str) -> str:
    if banco == "BBVA":
        return "Visa"
    if banco == "Banco Credicoop":
        # CABAL: tiene "R.N.P.S.P." o "TNA AD.EFEC." en pág 1 (Visa Credicoop no los tiene)
        if (re.search(r"R\s*\.\s*N\s*\.\s*P\s*\.\s*S\s*\.\s*P", texto, re.I) or
                re.search(r"T\s*N\s*A\s+A\s*D\s*\.\s*E\s*F\s*E\s*C", texto, re.I)):
            return "Cabal"
        return "Visa"
    if banco == "Banco Santander":
        return "Visa"
    if re.search(r"tarjeta\s+de\s+cr[eé]dito", texto, re.I):
        return "Tarjeta de Crédito"
    return "Resumen Bancario"


# ─────────────────────────────────────────────────────────────────────────────
# PARSERS POR BANCO — vencimiento actual + próximo vencimiento + montos
# ─────────────────────────────────────────────────────────────────────────────

def _parsear_bbva(texto: str) -> dict:
    """
    Layout BBVA (columnas separadas por línea):
    Línea N:   CIERRE ACTUAL  VENCIMIENTO ACTUAL  SALDO ACTUAL $ ...
    Línea N+1: 29-Ene-26  06-Feb-26  2.939.213,54  0,00  1.410.620,00

    Línea M:   CIERRE ANTERIOR  VENCIMIENTO ANTERIOR  PRÓXIMO CIERRE  PRÓXIMO VENCIMIENTO
    Línea M+2: 31-Dic-25  09-Ene-26  26-Feb-26  06-Mar-26
    """
    lineas = texto.split("\n")
    fecha_actual = None
    fecha_prox   = None
    monto        = None

    for i, linea in enumerate(lineas):
        # Vencimiento actual + monto
        if "VENCIMIENTO ACTUAL" in linea.upper() and i + 1 < len(lineas):
            sig = lineas[i + 1]
            tokens_f = re.findall(r"\d{1,2}-[A-Za-záéíóúü]{3}-\d{2,4}", sig)
            if len(tokens_f) >= 2:
                p = tokens_f[1].split("-")
                fecha_actual = _fecha_desde_abrev(p[0], p[1], p[2])
            sin_fechas = re.sub(r"\d{1,2}-[A-Za-záéíóúü]{3}-\d{2,4}", "", sig)
            m = re.search(r"(\d{1,3}(?:\.\d{3})+,\d{2})", sin_fechas)
            if m:
                monto = _normalizar_monto(m.group(1))

        # Próximo vencimiento — layout "Otros períodos"
        if "PRÓXIMO VENCIMIENTO" in linea.upper() and i + 2 < len(lineas):
            sig2 = lineas[i + 2] if "Otros" in lineas[i + 1] else lineas[i + 1]
            tokens_f2 = re.findall(r"\d{1,2}-[A-Za-záéíóúü]{3}-\d{2,4}", sig2)
            if len(tokens_f2) >= 4:
                p = tokens_f2[3].split("-")
                fecha_prox = _fecha_desde_abrev(p[0], p[1], p[2])

    return {"fecha": fecha_actual, "fecha_prox": fecha_prox, "monto": monto}


def _parsear_credicoop(texto: str) -> dict:
    """
    Credicoop (Visa y Cabal) — campos con letras espaciadas.
    Vencimiento actual: "V E N C I M I E N T O A C T U A L : 12/03/2026"
    Próximo vto (CABAL): "PR O X I M O V T O 10/04/2026" (en misma línea)
    Próximo vto (Visa):  "C I E R R E A N T E R I O R 29 Ene 26 PR O X I M O V T O 08 Abr 26"
    """
    fecha_actual = None
    fecha_prox   = None
    monto        = None

    # Vencimiento actual — formato DD/MM/AAAA
    m = re.search(
        r"V\s*E\s*N\s*C\s*I\s*M\s*I\s*E\s*N\s*T\s*O\s+A\s*C\s*T\s*U\s*A\s*L\s*[:\s]+(\d{1,2}/\d{2}/\d{4})",
        texto, re.I
    )
    if m:
        fecha_actual = _fecha_desde_ddmmaaaa(m.group(1))

    # Vencimiento actual — formato "11 Mar 26"
    if not fecha_actual:
        m2 = re.search(
            r"V\s*E\s*N\s*C\s*I\s*M\s*I\s*E\s*N\s*T\s*O\s+A\s*C\s*T\s*U\s*A\s*L\s*[:\s]+(\d{1,2})\s+([A-Za-z]+)\s+(\d{2,4})",
            texto, re.I
        )
        if m2:
            fecha_actual = _fecha_desde_abrev(m2.group(1), m2.group(2), m2.group(3))

    # Próximo vencimiento — "P RO X I M O V T O 10/04/2026" (CABAL)
    # o "P R O X I M O V T O 08 Abr 26" (Credicoop Visa)
    # Patrón flexible: P con espaciado variable antes de ROXIMO VTO
    m3 = re.search(
        r"P\s*R\s*O\s*X\s*I\s*M\s*O\s+V\s*T\s*O\s+(\d{1,2}/\d{2}/\d{4})",
        texto, re.I
    )
    if m3:
        fecha_prox = _fecha_desde_ddmmaaaa(m3.group(1))

    if not fecha_prox:
        m4 = re.search(
            r"P\s*R\s*O\s*X\s*I\s*M\s*O\s+V\s*T\s*O\s+(\d{1,2})\s+([A-Za-z]{3})\s+(\d{2,4})",
            texto, re.I
        )
        if m4:
            fecha_prox = _fecha_desde_abrev(m4.group(1), m4.group(2), m4.group(3))

    # Saldo con letras espaciadas
    ms = re.search(
        r"S\s*A\s*L\s*D?\s*O\s+A\s*C\s*T\s*U\s*A\s*L\s+\$\s*[:\s]+([\d.,]+)",
        texto, re.I
    )
    if ms:
        monto = _normalizar_monto(ms.group(1))

    if not monto:
        md = re.search(r"DEBITAREMOS[^\n]+\$\s*([\d.,]+)", texto, re.I)
        if md:
            monto = _normalizar_monto(md.group(1))

    return {"fecha": fecha_actual, "fecha_prox": fecha_prox, "monto": monto}


def _parsear_santander(texto: str) -> dict:
    """
    Santander Río:
    - Vencimiento actual: "VENCIMIENTO 06 Abr 26"
    - Próximo vencimiento: "Prox.Vto.: 04 May 26"
    - Monto a pagar (última pág): "DEBITAREMOS ... $ 12264290,95 + U$S 6121,75"
      o en bloque final: "12264.290,95  6.121,75"
    """
    fecha_actual = None
    fecha_prox   = None
    monto        = None
    monto_usd    = None

    m = re.search(r"VENCIMIENTO\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{2,4})", texto, re.I)
    if m:
        fecha_actual = _fecha_desde_abrev(m.group(1), m.group(2), m.group(3))

    m2 = re.search(r"Prox\.Vto\.\s*[:\s]+(\d{1,2})\s+([A-Za-z]+)\s+(\d{2,4})", texto, re.I)
    if m2:
        fecha_prox = _fecha_desde_abrev(m2.group(1), m2.group(2), m2.group(3))

    # 1. Buscar "DEBITAREMOS ... SUMA DE $ 12264290,95 + U$S 6121,75"
    md = re.search(r"DEBITAREMOS[^\n]+\$\s*([\d.,]+)\s*\+\s*U\$S\s*([\d.,]+)", texto, re.I)
    if md:
        monto     = _normalizar_monto(md.group(1))
        monto_usd = _normalizar_monto(md.group(2))

    # 2. Buscar DEBITAREMOS con U$S sin el +
    if not monto:
        md2 = re.search(r"DEBITAREMOS[^\n]+\$\s*([\d.,]+)[^\n]*U\$S\s*([\d.,]+)", texto, re.I)
        if md2:
            monto     = _normalizar_monto(md2.group(1))
            monto_usd = _normalizar_monto(md2.group(2))

    # 3. Si no encontró USD, buscar solo pesos
    if not monto:
        md3 = re.search(r"DEBITAREMOS[^\n]+\$\s*([\d.,]+)", texto, re.I)
        if md3:
            monto = _normalizar_monto(md3.group(1))

    # 4. Bloque final: "12264.290,95  6.121,75" (dos números al final del texto)
    if not monto:
        mb = re.search(r"(\d{1,3}\.\d{3}[\d.,]*,\d{2})\s+(\d{1,3}\.\d{3},\d{2})\s*$", texto.strip())
        if mb:
            monto     = _normalizar_monto(mb.group(1))
            monto_usd = _normalizar_monto(mb.group(2))

    return {"fecha": fecha_actual, "fecha_prox": fecha_prox, "monto": monto, "monto_usd": monto_usd}


def _parsear_generico(texto: str) -> dict:
    fecha_actual = None
    monto        = None
    for patron in [
        r"vencimiento[:\s]+(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})",
        r"fecha\s+de\s+vencimiento[:\s]+(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})",
    ]:
        m = re.search(patron, texto, re.I)
        if m:
            a = int(m.group(3))
            if a < 100: a += 2000
            try:
                fecha_actual = date(a, int(m.group(2)), int(m.group(1)))
                break
            except ValueError:
                pass
    for patron in [
        r"total\s+a\s+pagar[:\s]+\$?\s*([\d.,]+)",
        r"saldo\s+actual[:\s]+\$?\s*([\d.,]+)",
        r"DEBITAREMOS[^\n]+\$\s*([\d.,]+)",
    ]:
        m = re.search(patron, texto, re.I)
        if m:
            monto = _normalizar_monto(m.group(1))
            if monto: break
    return {"fecha": fecha_actual, "fecha_prox": None, "monto": monto}


def _parsear_monto_usd(texto: str) -> float:
    """Extrae el saldo total en dólares. Busca por línea para evitar falsos positivos."""
    for linea in texto.split("\n"):
        # "SALDO ACTUAL $9351.748,93 U $ S 12.518,70" (Santander)
        m = re.search(r"SALDO\s+ACTUAL\s+\$[\d.,]+\s+U\s*\$\s*S\s+([\d.,]+)", linea, re.I)
        if m:
            v = _normalizar_monto(m.group(1))
            if v and v >= 10:
                return v
        # "S A L D O A C T U A L U $ S : 16.759,28" (Credicoop con letras espaciadas)
        m2 = re.search(
            r"S\s*A\s*L\s*D\s*O\s+A\s*C\s*T\s*U\s*A\s*L\s+U\s*\$\s*S\s*[:\s]+([\d.,]+)",
            linea, re.I
        )
        if m2:
            v = _normalizar_monto(m2.group(1))
            if v and v >= 10:
                return v
        # "DEBITAREMOS ... + U$S 16759,28" (Credicoop última página)
        m3 = re.search(r"DEBITAREMOS[^\n]+U\s*\$\s*S\s+([\d.,]+)", linea, re.I)
        if m3:
            v = _normalizar_monto(m3.group(1))
            if v and v >= 10:
                return v
    return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def analizar_pdf(file_bytes: bytes, nombre_archivo: str) -> dict:
    texto  = extraer_texto_pdf(file_bytes)
    banco  = _detectar_banco(texto)
    tipo   = _detectar_tipo(texto, banco)

    if banco == "BBVA":
        datos = _parsear_bbva(texto)
    elif banco == "Banco Credicoop":
        datos = _parsear_credicoop(texto)
    elif banco == "Banco Santander":
        datos = _parsear_santander(texto)
    else:
        datos = _parsear_generico(texto)

    fecha_venc       = datos["fecha"]
    fecha_prox_venc  = datos.get("fecha_prox")
    monto            = datos["monto"]
    monto_usd        = _parsear_monto_usd(texto)

    fecha_habil      = siguiente_dia_habil(fecha_venc) if fecha_venc else None
    fecha_prox_habil = siguiente_dia_habil(fecha_prox_venc) if fecha_prox_venc else None
    ajustada         = (fecha_habil != fecha_venc) if (fecha_habil and fecha_venc) else False

    campos_ok = sum([banco != "Banco Desconocido", monto is not None, fecha_venc is not None])
    confianza = {3: "alta", 2: "media"}.get(campos_ok, "baja")

    return {
        "banco":              banco,
        "tipo":               tipo,
        "monto":              monto,
        "monto_usd":          monto_usd,
        "fecha_vencimiento":  fecha_venc,
        "fecha_pago_habil":   fecha_habil,
        "fecha_prox_venc":    fecha_prox_venc,
        "fecha_prox_habil":   fecha_prox_habil,
        "ajustada":           ajustada,
        "texto_raw":          texto[:2000],
        "origen_pdf":         nombre_archivo,
        "confianza":          confianza,
        "error":              None,
    }


def analizar_multiples_pdfs(archivos: list) -> list:
    resultados = []
    for nombre, contenido in archivos[:4]:
        try:
            r = analizar_pdf(contenido, nombre)
        except Exception as e:
            r = {
                "banco": "Error de lectura", "tipo": "—",
                "monto": None, "monto_usd": 0.0,
                "fecha_vencimiento": None, "fecha_pago_habil": None,
                "fecha_prox_venc": None, "fecha_prox_habil": None,
                "ajustada": False, "texto_raw": "",
                "origen_pdf": nombre, "confianza": "baja", "error": str(e),
            }
        resultados.append(r)
    return resultados
