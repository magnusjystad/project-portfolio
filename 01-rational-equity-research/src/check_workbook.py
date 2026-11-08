"""Recalculates model/rational_model.xlsx with LibreOffice (headless) and checks the formulas reproduce src/model.py.

    python src/check_workbook.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
from openpyxl import load_workbook

from src import model as M


def recalc(path):
    out = Path(tempfile.mkdtemp())
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(out), str(path)],
                   check=True, capture_output=True, timeout=300)
    return load_workbook(out / path.name, data_only=True)


def find(ws, label, col="B", start=1):
    for r in range(start, ws.max_row + 1):
        if ws[f"A{r}"].value == label:
            return ws[f"{col}{r}"].value, r
    raise KeyError(label)


if __name__ == "__main__":
    wb = recalc(ROOT / "model" / "rational_model.xlsx")
    mk = M.market_inputs()
    vals, tp = M.valuation(mk["ke"])
    D = wb["DCF"]
    ok = True
    start = 1
    for s in ["Bear", "Base", "Bull"]:
        _, r0 = find(D, None, start=start) if False else (None, start)
        ev, r = find(D, "Enterprise value", start=start)
        t12, r2 = find(D, "12-month target (EUR) = value × (1 + ke) − dividend", start=start)
        start = r2 + 1
        print(f"{s}: EV excel {ev:,.2f} python {vals[s]['ev']:,.2f} | target excel {t12:,.2f} python {vals[s]['target']:,.2f}")
        ok &= abs(ev - vals[s]["ev"]) < 0.01 and abs(t12 - vals[s]["target"]) < 0.01
    X = wb["Scenarios"]
    wtp, _ = find(X, "Probability-weighted 12-month price target (EUR)")
    rating, _ = find(X, "Rating (Buy ≥ +15%, Sell ≤ −10%, else Hold)")
    Z = wb["Sensitivity"]
    centre = Z["D7"].value
    print(f"Weighted target excel {wtp:,.2f} python {tp:,.2f} | sensitivity centre {centre:,.2f} | rating {rating} ({M.rating(tp, mk['price'])[0]})")
    ok &= abs(wtp - tp) < 0.01 and abs(centre - tp) < 0.01 and rating == M.rating(tp, mk["price"])[0]
    H = wb["History"]
    chk = [H.cell(row=r, column=c).value for r in range(1, H.max_row + 1) if H[f"A{r}"].value == "Check: regions − sales" for c in range(3, 13)]
    print("regions − sales check:", max(abs(x) for x in chk))
    ok &= max(abs(x) for x in chk) < 0.01
    O = wb["ROIC"]
    ro = M.roic_history()
    xr = [O.cell(row=7, column=3 + i).value for i in range(10)]
    print("ROIC max abs diff:", max(abs(a - b) for a, b in zip(xr, ro["roic"].values)))
    ok &= max(abs(a - b) for a, b in zip(xr, ro["roic"].values)) < 1e-6
    print("ALL CHECKS PASS" if ok else "CHECK FAILED")
    sys.exit(0 if ok else 1)
