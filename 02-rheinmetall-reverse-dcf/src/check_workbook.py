"""Recalculates model/rheinmetall_reverse_dcf.xlsx in LibreOffice and checks it against src/model.py.

    python src/check_workbook.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT)]
from openpyxl import load_workbook

from src import model as M


def recalc(path):
    out = Path(tempfile.mkdtemp())
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(out), str(path)],
                   check=True, capture_output=True, timeout=300)
    return load_workbook(out / path.name, data_only=True)


def find(ws, label, start=1):
    for r in range(start, ws.max_row + 1):
        if ws[f"A{r}"].value == label:
            return ws[f"B{r}"].value, r
    raise KeyError(label)


if __name__ == "__main__":
    wb = recalc(ROOT / "model" / "rheinmetall_reverse_dcf.xlsx")
    R = M.run()
    ok = True
    I = wb["Inputs"]
    wacc_x = find(I, "WACC")[0]; kd_x = find(I, "Bond yield to maturity (Excel YIELD, settlement 9 Oct 2026)")[0]
    print(f"WACC excel {wacc_x:.6f} python {R['mk']['wacc']:.6f} | YTM excel {kd_x:.6f} python {R['mk']['kd']:.6f}")
    ok &= abs(wacc_x - R["mk"]["wacc"]) < 2e-5 and abs(kd_x - R["mk"]["kd"]) < 2e-5
    Rv = wb["Reverse DCF"]
    d1, r1 = find(Rv, "Difference to share price")
    d2, _ = find(Rv, "Difference to share price", r1 + 1)
    print(f"(a) difference to price {d1:.4f} | (b) difference to price {d2:.4f}")
    ok &= abs(d1) < 0.5 and abs(d2) < 0.5
    C = wb["Cases"]
    start = 1
    for n in ["Bear", "Base", "Bull"]:
        v, r = find(C, "Value per share (EUR)", start); start = r + 1
        print(f"{n}: excel {v:,.2f} python {R['case_val'][n]['per_share']:,.2f}")
        ok &= abs(v - R["case_val"][n]["per_share"]) < 0.5
    G = wb["Grid"]
    g = R["grid"]
    for (i, j) in [(0, 0), (4, 5), (8, 10)]:
        x = G.cell(row=4 + i, column=2 + j).value
        p = g.iloc[i, j]
        print(f"grid[{g.index[i]}, {g.columns[j]}] excel {x:,.1f} python {p:,.1f}")
        ok &= abs(x - p) < 0.5
    T = wb["Tests"]
    print("recommendation:", T["B9"].value, "| budget implied/base/bull", [round(T[f"{c}4"].value, 4) for c in "BDE"],
          "python", round(R["tests"]["budget"]["implied"], 4))
    ok &= abs(T["B4"].value - R["tests"]["budget"]["implied"]) < 1e-4
    print("ALL CHECKS PASS" if ok else "CHECK FAILED")
    sys.exit(0 if ok else 1)
