"""Laster ned PEFs kvartalsrapporter (kildene for eksempeltallene) til data/kilde/.

    python src/hent_kilder.py
"""
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[1] / "data" / "kilde"
URL = "https://share.paretosec.com/upload/files/PEF%20{q}%202026.pdf"   # lenket fra paretoai.no/reports

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for q in ["Q1", "Q2", "Q3"]:
        r = requests.get(URL.format(q=q), timeout=120)
        r.raise_for_status()
        (OUT / f"PEF_{q}_2026.pdf").write_bytes(r.content)
        print(q, len(r.content))
