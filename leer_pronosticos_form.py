"""
leer_pronosticos_form.py — Lee las respuestas de un Google Form (publicado como CSV)
y mete los pronosticos de eliminatorias en pronosticos.json.

Cómo se conecta con el resto del flujo:
  1. Los jugadores llenan el Google Form (un campo "Nombre" + un campo de texto
     por cada cruce). Dos tipos de pregunta:
       - 16avos (equipo real ya confirmado): título "España vs Francia".
       - Octavos en adelante (equipo todavia no se sabe): título con
         "Partido <id>" en el texto, ej. "Partido 1088 (Ganador de 1074 vs 1077)".
         El id debe coincidir con calendario.json / estructura_bracket.json.
  2. El Form guarda las respuestas en una Google Sheet.
  3. Esa Sheet se publica a la web como CSV (Archivo > Compartir > Publicar en la
     Web > Formato CSV) — eso da una URL pública que este script puede leer sin
     necesitar login ni API key de Google.
  4. Este script cruza cada columna del CSV (que tiene el nombre de los dos
     equipos) contra calendario.json para saber a qué id de partido corresponde,
     y escribe la predicción de cada jugador en pronosticos.json.
  5. actualizar_api.py ya lee pronosticos.json normalmente, así que después de
     correr este script solo falta correr actualizar_api.py como siempre.

Requiere:
  pip install requests
  La URL del CSV publicado guardada en config.json:
    {"form_csv_url": "https://docs.google.com/.../pub?output=csv"}

IMPORTANTE: para que el cruce funcione, calendario.json debe tener ya el nombre
real de los equipos en los cruces de eliminatoria (no "Equipo A vs Equipo Q").
Edita calendario.json a mano reemplazando esos placeholders en cuanto se
confirme el bracket.
"""

import csv
import io
import json
import os
import re
import unicodedata

import requests

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CALENDARIO  = os.path.join(BASE_DIR, "calendario.json")
PRONOSTICOS = os.path.join(BASE_DIR, "pronosticos.json")
CONFIG      = os.path.join(BASE_DIR, "config.json")

JUGADORES = ['Yosember','Josmary','Carlos','Osmar','Jonathan','Sol','Mayra','Peter','Carolina','Jose']

PATRON_PARTIDO = re.compile(r"^(.*?)\s+vs\s+(.*?)$", re.IGNORECASE)
PATRON_ABSTRACTO = re.compile(r"partido\s+(\d+)", re.IGNORECASE)
PATRON_MARCADOR = re.compile(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$")


def normaliza(nombre):
    s = nombre.strip().lower()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def cargar_config():
    if not os.path.exists(CONFIG):
        raise SystemExit(f"Falta {CONFIG}.")
    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    url = cfg.get("form_csv_url")
    if not url:
        raise SystemExit(
            'config.json no tiene "form_csv_url". Publica la Sheet del Form como CSV '
            "(Archivo > Compartir > Publicar en la Web) y pega esa URL en config.json."
        )
    return url


def descargar_csv(url):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return list(csv.DictReader(io.StringIO(resp.text)))


def mapear_columnas_a_ids(columnas, calendario):
    """Para cada columna de partido en el CSV, encuentra el id del calendario interno.

    Soporta dos formatos de pregunta:
      - Por nombre real de equipo, ej. "Sudáfrica vs Canadá" (16avos confirmados).
      - Por referencia abstracta, ej. "Partido 1088 (Ganador de 1074 vs 1077)"
        (Octavos en adelante, antes de saber los equipos reales).
    """
    indice = {}
    for p in calendario:
        indice[(normaliza(p["local"]), normaliza(p["visitante"]))] = (p["id"], False)
        indice[(normaliza(p["visitante"]), normaliza(p["local"]))] = (p["id"], True)

    mapa, sin_match = {}, []
    for col in columnas:
        m_abs = PATRON_ABSTRACTO.search(col)
        if m_abs:
            mapa[col] = (int(m_abs.group(1)), False)
            continue
        m = PATRON_PARTIDO.search(col.split(":", 1)[-1].strip()) if ":" in col else PATRON_PARTIDO.search(col)
        if not m:
            continue
        local, visitante = m.group(1).strip(), m.group(2).strip()
        clave = (normaliza(local), normaliza(visitante))
        if clave in indice:
            id_, invertido = indice[clave]
            mapa[col] = (id_, invertido)
        else:
            sin_match.append(col)
    return mapa, sin_match


def main():
    url = cargar_config()
    with open(CALENDARIO, encoding="utf-8") as f:
        calendario = json.load(f)
    if os.path.exists(PRONOSTICOS):
        with open(PRONOSTICOS, encoding="utf-8") as f:
            pronosticos = json.load(f)
    else:
        pronosticos = {}

    print("Descargando respuestas del formulario...")
    filas = descargar_csv(url)
    if not filas:
        print("El formulario no tiene respuestas todavia.")
        return

    columnas_partido = [c for c in filas[0].keys() if c not in ("Marca temporal", "Nombre")]
    mapa_cols, sin_match = mapear_columnas_a_ids(columnas_partido, calendario)
    if sin_match:
        print(f"  AVISO: {len(sin_match)} columnas del formulario no se pudieron cruzar con calendario.json "
              "(revisa que los nombres de equipo coincidan exactamente):")
        for c in sin_match:
            print(f"    {c}")

    # Si un jugador respondio mas de una vez, se queda la ultima respuesta (la mas reciente).
    ultima_por_jugador = {}
    for fila in filas:
        nombre = (fila.get("Nombre") or "").strip()
        if nombre in JUGADORES:
            ultima_por_jugador[nombre] = fila

    actualizados = 0
    for jugador, fila in ultima_por_jugador.items():
        pronosticos.setdefault(jugador, {})
        for col, (id_, invertido) in mapa_cols.items():
            valor = (fila.get(col) or "").strip()
            m = PATRON_MARCADOR.match(valor)
            if not m:
                continue
            a, b = int(m.group(1)), int(m.group(2))
            pred_l, pred_v = (b, a) if invertido else (a, b)
            pronosticos[jugador][str(id_)] = {"pred_l": pred_l, "pred_v": pred_v}
            actualizados += 1

    with open(PRONOSTICOS, "w", encoding="utf-8") as f:
        json.dump(pronosticos, f, ensure_ascii=False, indent=2)

    print(f"pronosticos.json actualizado - {actualizados} predicciones de eliminatorias guardadas "
          f"de {len(ultima_por_jugador)} jugadores.")


if __name__ == "__main__":
    main()
