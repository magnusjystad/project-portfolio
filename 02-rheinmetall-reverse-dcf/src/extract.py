"""Rheinmetall key figures 2019–2025 from the 2025 annual report's multi-year table (continuing operations as restated
in that report) and H1 2026 figures from the half-yearly report. Writes data/history.csv and data/h1_2026.csv.

    python src/extract.py      (needs the PDFs in data/source/)
"""
import re
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "source"
NUM = r"\(?-?[\d,]+(?:\.\d+)?\)?|-"
ROWS = {  # label in the key-figures table -> output name
    r"^\s*Sales\s+€ million": "Sales",
    r"Operating result2, 5\s+€ million": "Operating result",
    r"EBIT5\s+€ million": "EBIT",
    r"Order Intake\s+€ million": "Order intake",
    r"Rheinmetall Nomination\s+€ million": "Rheinmetall Nomination",
    r"Rheinmetall Backlog \(12/31\)\s+€ million": "Rheinmetall Backlog",
    r"Cash flow from operating activities\s+€ million": "Operating cash flow",
    r"Of which continuing operations5\s+€ million": "Operating free cash flow (continuing)",
    r"Return on capital employed \(ROCE\)3, 5, 6\s+%": "ROCE %",
    r"Cash Conversion Rate7\s+%": "Cash conversion rate %",
}


def num(s):
    s = s.strip()
    if s in ("-", ""):
        return None
    neg = s.startswith("(")
    v = float(s.strip("()").replace(",", ""))
    return -v if neg else v


def text(pdf):
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout


def history():
    t = text(SRC / "Rheinmetall-Annual-Report-2025.pdf")
    t = t[t.index("SALES/EARNINGS"): t.index("SALES/EARNINGS") + 20000]
    years = [2025, 2024, 2023, 2022, 2021, 2020, 2019]
    out = {}

    def after(line, pat):
        """Numbers that follow the label (and its unit) up to the next word."""
        m = re.search(pat, line)
        rest = line[m.end():]
        rest = re.split(r"\s{2,}[A-Za-z]", rest)[0]
        return [num(v) for v in re.findall(NUM, rest)][:7]

    for line in t.splitlines():
        for pat, name in list(ROWS.items()) + [(r"investment property\s+€ million", "Capex"),
                                               (r"Net financial debt \(-\)/Net liquidity \(\+\)4\s+€ million", "Net liquidity (+)/net financial debt (-)"),
                                               (r"Dividend per share\s+€", "Dividend per share"), (r"Stock price \(12/31\)\s+€", "Share price (31 Dec)"),
                                               (r"\bEquity5\s+€ million", "Equity")]:
            if re.search(pat, line) and name not in out:
                v = after(line, pat)
                if v:
                    out[name] = dict(zip(years, v))
    H = pd.DataFrame(out).T[sorted(years)]
    H.to_csv(ROOT / "data" / "history.csv")
    return H


if __name__ == "__main__":
    print(history().to_string())
