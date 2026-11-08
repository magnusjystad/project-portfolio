"""Extract the J.P. Morgan 2026 LTCMA U.S. dollar assumption matrix from the public PDF."""
import re
from pathlib import Path

import numpy as np
import pandas as pd
import requests

URL = "https://am.jpmorgan.com/content/dam/jpm-am-aem/global/en/insights/ltcma-2026-us-matrix_usd.pdf"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
# ETF -> LTCMA asset class (closest match)
MAP = {"SPY": "U.S. Large Cap", "EFA": "EAFE Equity", "EEM": "Emerging Markets Equity",
       "IEF": "U.S. Intermediate Treasuries", "TLT": "U.S. Long Treasuries", "TIP": "TIPS",
       "LQD": "U.S. Inv Grade Corporate Bonds", "HYG": "U.S. High Yield Bonds",
       "VNQ": "U.S. REITs", "GLD": "Gold", "DBC": "Commodities"}
EXTRA = ["U.S. Inflation", "U.S. Cash"]


def parse(pdf_path: Path):
    from pypdf import PdfReader
    text = PdfReader(str(pdf_path)).pages[1].extract_text()
    rows = []
    num = r"-?\d+\.\d+"
    for line in text.splitlines():
        m = re.match(rf"^(.*?[A-Za-z\)])\s+((?:{num}\s*)+)$", line.strip())
        if m:
            vals = [float(v) for v in re.findall(num, m.group(2))]
            rows.append((m.group(1).strip(), vals))
    names = [n for n, _ in rows]
    # Row i holds 4 statistics then i+1 correlations (lower triangle incl. diagonal)
    stats, corr = {}, np.eye(len(rows))
    for i, (n, v) in enumerate(rows):
        assert len(v) == 4 + i + 1, (n, len(v), i)
        stats[n] = {"Compound 2026": v[0] / 100, "Arithmetic 2026": v[1] / 100,
                    "Volatility": v[2] / 100, "Compound 2025": v[3] / 100}
        corr[i, :i + 1] = v[4:]
        corr[:i + 1, i] = v[4:]
    return pd.DataFrame(stats).T, pd.DataFrame(corr, index=names, columns=names)


def load(data_dir: Path, refresh=False):
    """Returns (assumptions for the 11 ETFs + inflation and cash, correlation matrix)."""
    a_csv, c_csv = data_dir / "ltcma2026_usd_assumptions.csv", data_dir / "ltcma2026_usd_correlations.csv"
    if a_csv.exists() and not refresh:
        return pd.read_csv(a_csv, index_col=0), pd.read_csv(c_csv, index_col=0)
    pdf = data_dir / "_ltcma2026_usd.pdf"
    pdf.write_bytes(requests.get(URL, headers=UA, timeout=120).content)
    stats, corr = parse(pdf)
    pdf.unlink()  # the source PDF is not redistributed; the extracted figures are cited
    keep = list(MAP.values()) + EXTRA
    a = stats.loc[keep].copy()
    a.insert(0, "ETF", [k for k in MAP] + ["", ""])
    c = corr.loc[keep, keep]
    a.to_csv(a_csv)
    c.to_csv(c_csv)
    return a, c
