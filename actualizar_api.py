"""
actualizar_api.py — Genera datos.json sin depender del Excel.

Fuente de resultados: football-data.org — https://www.football-data.org/
  Competición: Mundial (código "WC"). Plan gratis: 10 requests/minuto.
Fuente de pronósticos: pronosticos.json (predicciones de cada jugador, ya no en Excel)
Fuente del calendario: calendario.json (qué equipos juegan en cada id de partido)

Requiere:
  pip install requests
  Un token gratuito guardado en config.json:
    {"football_data_token": "TU_TOKEN_AQUI"}
  (se consigue registrándose en https://www.football-data.org/client/register)
"""

import json, os, unicodedata
from datetime import datetime
import requests

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CALENDARIO  = os.path.join(BASE_DIR, "calendario.json")
PRONOSTICOS = os.path.join(BASE_DIR, "pronosticos.json")
CONFIG      = os.path.join(BASE_DIR, "config.json")
JSON_OUT    = os.path.join(BASE_DIR, "datos.json")

JUGADORES = ['Yosember','Josmary','Carlos','Osmar','Jonathan','Sol','Mayra','Peter','Carolina','Jose']

API_BASE   = "https://api.football-data.org/v4"
COMPETICION = "WC"   # Código del Mundial en football-data.org

# Nombres como los devuelve football-data.org (en inglés) para cada nombre interno en español.
# Si algún cruce falla, revisar el nombre exacto que imprime main() en "SIN CRUZAR" y ajustar aquí.
TRADUCCIONES = {
    "Alemania": "Germany", "Arabia Saudí": "Saudi Arabia", "Argelia": "Algeria",
    "Argentina": "Argentina", "Australia": "Australia", "Austria": "Austria",
    "Bosnia y Herz.": "Bosnia-Herzegovina", "Brasil": "Brazil", "Bélgica": "Belgium",
    "Cabo Verde": "Cape Verde Islands", "Canadá": "Canada", "Catar": "Qatar",
    "Chequia": "Czechia", "Colombia": "Colombia", "Corea del Sur": "South Korea",
    "Costa de Marfil": "Ivory Coast", "Croacia": "Croatia", "Curaçao": "Curaçao",
    "DR Congo": "Congo DR", "Ecuador": "Ecuador", "Egipto": "Egypt", "Escocia": "Scotland",
    "España": "Spain", "Francia": "France", "Ghana": "Ghana", "Haití": "Haiti",
    "Inglaterra": "England", "Irak": "Iraq", "Irán": "Iran", "Japón": "Japan",
    "Jordania": "Jordan", "Marruecos": "Morocco", "México": "Mexico", "Noruega": "Norway",
    "Nueva Zelanda": "New Zealand", "Panamá": "Panama", "Paraguay": "Paraguay",
    "Países Bajos": "Netherlands", "Portugal": "Portugal", "Senegal": "Senegal",
    "Sudáfrica": "South Africa", "Suecia": "Sweden", "Suiza": "Switzerland",
    "Turquía": "Turkey", "Túnez": "Tunisia", "USA": "United States", "Uruguay": "Uruguay",
    "Uzbekistán": "Uzbekistan",
}


def cargar_config():
    if not os.path.exists(CONFIG):
        raise SystemExit(
            f"Falta {CONFIG}. Crea el archivo con:\n"
            '  {"football_data_token": "TU_TOKEN_AQUI"}'
        )
    with open(CONFIG, encoding="utf-8") as f:
        cfg = json.load(f)
    token = cfg.get("football_data_token")
    if not token:
        raise SystemExit("config.json no tiene 'football_data_token'.")
    return token


def obtener_partidos(token):
    """Descarga todos los partidos del Mundial desde football-data.org."""
    url = f"{API_BASE}/competitions/{COMPETICION}/matches"
    headers = {"X-Auth-Token": token}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json().get("matches", [])


def traducir(nombre):
    return TRADUCCIONES.get(nombre, nombre)


def normaliza(nombre):
    s = traducir(nombre).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s


def emparejar_resultados(calendario, partidos_api):
    """Cruza cada partido del calendario interno con su partido real por nombre de equipo."""
    indice = {}
    for m in partidos_api:
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        if not home or not away:
            continue  # fase eliminatoria sin equipos definidos aún
        indice[(normaliza(home), normaliza(away))] = (m, False)
        indice[(normaliza(away), normaliza(home))] = (m, True)  # invertido

    resultado, sin_cruzar = [], []
    for partido in calendario:
        key = (normaliza(partido["local"]), normaliza(partido["visitante"]))
        match = indice.get(key)
        entrada = dict(partido)
        gl = gv = None
        jugado = False
        en_vivo = False
        fecha = None
        if match:
            m, invertido = match
            estado = m.get("status")
            ft = m.get("score", {}).get("fullTime", {})
            h, a = ft.get("home"), ft.get("away")
            fecha = m.get("utcDate")
            if h is not None and a is not None:
                gl, gv = (a, h) if invertido else (h, a)
                jugado = estado == "FINISHED"
                en_vivo = estado in ("IN_PLAY", "PAUSED")
        else:
            sin_cruzar.append(partido)
        entrada["goles_l"] = gl
        entrada["goles_v"] = gv
        entrada["jugado"] = jugado
        entrada["en_vivo"] = en_vivo
        entrada["fecha"] = fecha
        resultado.append(entrada)
    return resultado, sin_cruzar


def calcular_pts(pred_l, pred_v, goles_l, goles_v):
    if pred_l is None or pred_v is None or goles_l is None or goles_v is None:
        return None
    if pred_l == goles_l and pred_v == goles_v:
        return 3
    signo_pred = (pred_l > pred_v) - (pred_l < pred_v)
    signo_real = (goles_l > goles_v) - (goles_l < goles_v)
    return 1 if signo_pred == signo_real else 0


def main():
    token = cargar_config()
    with open(CALENDARIO, encoding="utf-8") as f:
        calendario = json.load(f)
    with open(PRONOSTICOS, encoding="utf-8") as f:
        preds = json.load(f)

    print("Descargando resultados del Mundial desde football-data.org...")
    partidos_api = obtener_partidos(token)
    print(f"  {len(partidos_api)} partidos recibidos de la API")

    todos_partidos, sin_cruzar = emparejar_resultados(calendario, partidos_api)
    if sin_cruzar:
        print(f"  AVISO: {len(sin_cruzar)} partidos del calendario no se pudieron cruzar con la API "
              "(probablemente fase eliminatoria sin equipos definidos, o falta una traducción):")
        for p in sin_cruzar[:10]:
            print(f"    #{p['id']} {p['local']} vs {p['visitante']}")

    mapa = {p["id"]: p for p in todos_partidos}
    partidos_grupo_jugados = [p for p in todos_partidos if p["jugado"] and len(p["grupo"]) == 1]

    pronosticos = {}
    for jug in JUGADORES:
        partidos_jug = []
        pts_total = 0
        for id_str, pred in preds.get(jug, {}).items():
            id_  = int(id_str)
            real = mapa.get(id_)
            # Los puntos solo se calculan con el resultado FINAL; un partido en vivo
            # todavía puede cambiar de marcador, así que no cuenta hasta terminar.
            pts  = calcular_pts(pred["pred_l"], pred["pred_v"],
                                 real["goles_l"] if real and real["jugado"] else None,
                                 real["goles_v"] if real and real["jugado"] else None)
            if pts is not None:
                pts_total += pts
            if real and real["jugado"]:
                resultado = f'{real["local"]} {real["goles_l"]} - {real["goles_v"]} {real["visitante"]}'
            else:
                resultado = "Pendiente"
            partidos_jug.append({
                "id": id_, "pred_l": pred["pred_l"], "pred_v": pred["pred_v"],
                "pts": pts, "resultado": resultado,
            })
        partidos_jug.sort(key=lambda m: m["id"])
        pronosticos[jug] = {"pts_total": pts_total, "partidos": partidos_jug}

    ranking_lista = sorted(JUGADORES, key=lambda j: pronosticos[j]["pts_total"], reverse=True)
    max_pts = pronosticos[ranking_lista[0]]["pts_total"] if ranking_lista else 0

    ranking = []
    for i, name in enumerate(ranking_lista, 1):
        pts = pronosticos[name]["pts_total"]
        acumulado, total = [], 0
        for p in pronosticos[name]["partidos"]:
            if p["pts"] is not None:
                total += p["pts"]
                acumulado.append({"id": p["id"], "pts": total})
        ranking.append({"pos": i, "name": name, "pts": pts, "diff": pts - max_pts, "acumulado": acumulado})

    ultimos5 = sorted(partidos_grupo_jugados, key=lambda p: p["fecha"] or "", reverse=True)[:5]
    en_vivo = [p for p in todos_partidos if p.get("en_vivo")]

    jugados_antes = None
    if os.path.exists(JSON_OUT):
        try:
            with open(JSON_OUT, encoding="utf-8") as f:
                jugados_antes = json.load(f).get("stats", {}).get("jugados")
        except (json.JSONDecodeError, OSError):
            jugados_antes = None
    if jugados_antes is not None and len(partidos_grupo_jugados) < jugados_antes:
        print(f"  ALERTA: jugados bajo de {jugados_antes} a {len(partidos_grupo_jugados)} "
              "- posible dato incompleto de la API, revisar antes de confiar en este resultado")

    data = {
        "ok": True,
        "actualizado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "ranking": ranking,
        "pronosticos": pronosticos,
        "partidos": partidos_grupo_jugados,
        "todos_partidos": todos_partidos,
        "ultimos5": ultimos5,
        "en_vivo": en_vivo,
        "stats": {"jugados": len(partidos_grupo_jugados), "pendientes": 72 - len(partidos_grupo_jugados)},
    }

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"datos.json generado - {len(partidos_grupo_jugados)} partidos de grupo jugados, "
          f"lider: {ranking[0]['name']} ({ranking[0]['pts']} pts)")


if __name__ == "__main__":
    main()
