"""Recalculates model/grifols_credit_model.xlsx in LibreOffice and checks it against src/model.py.

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


def row_of(ws, label, col="A"):
    for r in range(1, ws.max_row + 1):
        if ws[f"{col}{r}"].value == label:
            return r
    raise KeyError(label)


OK = True


def check(name, x, p, tol):
    global OK
    good = x is not None and abs(x - p) <= tol
    OK &= good
    print(f"{'ok ' if good else 'BAD'} {name:<58} excel {x!s:>22}  python {p:.6f}")


if __name__ == "__main__":
    wb = recalc(ROOT / "model" / "grifols_credit_model.xlsx")
    R = M.run()
    C = wb["Capital structure"]
    for nm in ["7.500% senior secured notes", "7.125% senior secured notes", "3.875% senior unsecured notes"]:
        r = row_of(C, nm)
        y = R["yields"][nm]
        check(f"YTM {nm}", C[f"J{r}"].value, y["ytm"], 3e-4)
        check(f"YTW {nm}", C[f"N{r}"].value, y["ytw"], 3e-4)
        print("    worst:", C[f"O{r}"].value, "| python:", y["worst"])
    P = wb["Projections"]
    for down, top in [(False, 4), (True, 22)]:
        df = R["down" if down else "base"]
        for lab, plab in [("Adjusted EBITDA", "Adjusted EBITDA"), ("Cash interest", "Cash interest"),
                          ("FCF before dividends", "FCF pre-dividends"), ("Net leverage (x)", "Net leverage (x)")]:
            r = top + 1 + ["Revenue", "Adjusted EBITDA margin", "Adjusted EBITDA", "Cash interest", "Capex, IT & R&D", "Taxes",
                           "Working capital", "Other", "FCF before dividends", "Dividends", "Net debt (Credit Agreement), year end",
                           "Credit-agreement EBITDA", "Net leverage (x)", "Adjusted EBITDA / cash interest (x)"].index(lab)
            assert P[f"A{r}"].value == lab
            check(f"{'down' if down else 'base'} 2028 {lab}", P[f"E{r}"].value, df.loc[plab, 2028], 1e-3 if "x)" in lab else 0.5)
    r = row_of(P, "Net leverage (x)", "A")
    lev_rows = [i for i in range(1, P.max_row + 1) if P[f"A{i}"].value == "Net leverage (x)"]
    refi_r = lev_rows[-1]
    check("Oct-2028 leverage, base", P[f"B{refi_r}"].value, R["refi_base"]["Net leverage Oct 2028 (x)"], 1e-3)
    check("Oct-2028 leverage, downside", P[f"C{refi_r}"].value, R["refi_down"]["Net leverage Oct 2028 (x)"], 1e-3)
    W = wb["Recovery"]
    check("Recovery: EV", W["B5"].value, R["w_down"]["EV"], 0.5)
    check("Recovery: secured", W["B12"].value, R["w_down"]["Secured recovery"], 1e-6)
    check("Recovery: unsecured", W["B18"].value, R["w_down"]["Unsecured recovery"], 1e-6)
    for i, m in enumerate([3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5]):
        check(f"grid {m}x secured", W[f"C{27 + i}"].value, R["grid"].loc["Secured", m], 1e-6)
        check(f"grid {m}x unsecured", W[f"D{27 + i}"].value, R["grid"].loc["Unsecured", m], 1e-6)
    check("Breakeven multiple, secured", W["B36"].value, R["be_sec"], 1e-3)
    check("Breakeven multiple, unsecured", W["B37"].value, R["be_uns"], 1e-3)
    X = wb["Relative value"]
    rv = R["rv"]
    for c, k in [("B", "7.125% secured 2030"), ("C", "3.875% unsecured 2028")]:
        check(f"Bund matched {k}", X[f"{c}7"].value, rv.loc["Bund (matched)", k], 2e-5)
        check(f"Spread per turn {k}", X[f"{c}10"].value, rv.loc["spread per turn (bp)", k], 1.5)
        check(f"Expected return {k}", X[f"{c}14"].value, rv.loc["expected return", k], 3e-4)
    check("Gap", X["B16"].value, R["gap"], 4e-4)
    print("recommendation excel:", X["B17"].value, "| python:", R["rec"])
    OK &= X["B17"].value == R["rec"]
    E = wb["EBITDA and Gotham"]
    pr = row_of(E, "Proportionate leverage (x)")
    check("Proportionate leverage", E[f"B{pr}"].value, R["prop"]["Leverage"], 1e-6)
    print("ALL CHECKS PASS" if OK else "CHECKS FAILED")
    sys.exit(0 if OK else 1)
