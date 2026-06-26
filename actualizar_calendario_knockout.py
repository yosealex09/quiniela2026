"""
actualizar_calendario_knockout.py — Rellena los equipos reales de las rondas
eliminatorias en calendario.json en cuanto la API los va confirmando.

calendario.json trae 31 cruces de eliminatoria con nombres placeholder
("Equipo A", "Equipo Q", ...) porque al momento de generarlo el bracket no
estaba definido. La API (football-data.org) va revelando los equipos reales
grupo por grupo a medida que termina la fase de grupos.

Este script empareja cada cruce del calendario interno con el fixture real de
la API por RONDA + ORDEN CRONOLÓGICO (asumiendo que ambos listan los cruces
en el mismo orden de bracket). Solo reemplaza el placeholder cuando la API ya
tiene LOS DOS equipos confirmados; si solo se conoce uno, lo deja pendiente.

Imprime cada emparejamiento para que se pueda revisar a simple vista que la
fecha/ronda tiene sentido antes de confiar en el resultado.

Requiere: pip install requests, token en config.json (igual que actualizar_api.py)
"""

import json, os, shutil
from datetime import datetime
import requests

import actualizar_api as base  # reusa TRADUCCIONES, cargar_config, API_BASE

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CALENDARIO = os.path.join(BASE_DIR, "calendario.json")

# API (inglés) -> nuestra etiqueta de "grupo" en calendario.json
ETAPA_A_GRUPO = {
    "LAST_32": "16avos de Final",
    "LAST_16": "Octavos de Final",
    "QUARTER_FINALS": "Cuartos de Final",
    "SEMI_FINALS": "Semifinales",
    "FINAL": "Final",
}

TRADUCCION_INVERSA = {v: k for k, v in base.TRADUCCIONES.items()}


def al_espanol(nombre_en):
    return TRADUCCION_INVERSA.get(nombre_en, nombre_en)


def main():
    token = base.cargar_config()
    resp = requests.get(f"{base.API_BASE}/competitions/{base.COMPETICION}/matches",
                         headers={"X-Auth-Token": token}, timeout=20)
    resp.raise_for_status()
    fixtures = resp.json().get("matches", [])

    with open(CALENDARIO, encoding="utf-8") as f:
        calendario = json.load(f)

    backup_path = CALENDARIO.replace(".json", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    shutil.copy(CALENDARIO, backup_path)
    print(f"Backup de calendario.json guardado en {os.path.basename(backup_path)}")

    resueltos, pendientes = 0, 0
    for etapa, grupo_label in ETAPA_A_GRUPO.items():
        fx_etapa = sorted(
            [m for m in fixtures if m["stage"] == etapa],
            key=lambda m: m["utcDate"],
        )
        cal_etapa = sorted(
            [p for p in calendario if p["grupo"] == grupo_label],
            key=lambda p: p["id"],
        )
        if len(fx_etapa) != len(cal_etapa):
            print(f"AVISO: {grupo_label} tiene {len(cal_etapa)} cruces en calendario.json "
                  f"pero la API trae {len(fx_etapa)} — revisar antes de confiar en el orden.")

        for cal_p, fx in zip(cal_etapa, fx_etapa):
            home, away = fx["homeTeam"]["name"], fx["awayTeam"]["name"]
            if home and away:
                local_es, visitante_es = al_espanol(home), al_espanol(away)
                cambio = (cal_p["local"] != local_es or cal_p["visitante"] != visitante_es)
                cal_p["local"], cal_p["visitante"] = local_es, visitante_es
                resueltos += 1
                marca = "NUEVO" if cambio else "ok"
                print(f"  [{grupo_label}] #{cal_p['id']} {local_es} vs {visitante_es}  "
                      f"({fx['utcDate']}) [{marca}]")
            else:
                pendientes += 1

    with open(CALENDARIO, "w", encoding="utf-8") as f:
        json.dump(calendario, f, ensure_ascii=False, indent=2)

    print(f"\ncalendario.json actualizado - {resueltos} cruces resueltos, {pendientes} aun pendientes.")


if __name__ == "__main__":
    main()
