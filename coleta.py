import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("RAPIDAPI_KEY")
if not KEY:
    raise SystemExit("Defina RAPIDAPI_KEY no arquivo .env")

HOST = "sportapi7.p.rapidapi.com"
TORNEIO = 390        # Brasileirão Série B
TEMPORADA = 89840    # temporada 2026
TOTAL_RODADAS = 38
STATUS_FINAIS = {"finished", "canceled"}

RAW = Path("data/raw")
RAW.mkdir(parents=True, exist_ok=True)
HEADERS = {"x-rapidapi-key": KEY, "x-rapidapi-host": HOST}


def rodada_completa(arquivo):
    eventos = json.loads(arquivo.read_text(encoding="utf-8")).get("events", [])
    return bool(eventos) and all(e["status"]["type"] in STATUS_FINAIS for e in eventos)


def coletar_rodada(rodada):
    arquivo = RAW / f"rodada_{rodada:02d}.json"
    if arquivo.exists() and rodada_completa(arquivo):
        return "cache"

    url = (f"https://{HOST}/api/v1/unique-tournament/{TORNEIO}"
           f"/season/{TEMPORADA}/events/round/{rodada}")
    r = requests.get(url, headers=HEADERS, timeout=30)
    if r.status_code != 200:
        return f"erro {r.status_code}: {r.text[:120]}"

    arquivo.write_text(r.text, encoding="utf-8")
    time.sleep(1)
    return "baixada"


if __name__ == "__main__":
    for rodada in range(1, TOTAL_RODADAS + 1):
        print(f"Rodada {rodada:02d}: {coletar_rodada(rodada)}")