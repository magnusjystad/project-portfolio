"""Snapshot of bond ETF risk characteristics from each fund's page on ishares.com."""
import html
import re
from datetime import date

import pandas as pd
import requests

PAGES = {"TLT": "https://www.ishares.com/us/products/239454/ishares-20-year-treasury-bond-etf",
         "HYG": "https://www.ishares.com/us/products/239565/ishares-iboxx-high-yield-corporate-bond-etf",
         "IEF": "https://www.ishares.com/us/products/239456/ishares-710-year-treasury-bond-etf",
         "TIP": "https://www.ishares.com/us/products/239467/ishares-tips-bond-etf",
         "LQD": "https://www.ishares.com/us/products/239566/ishares-iboxx-investment-grade-corporate-bond-etf"}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"}
FIELDS = {"Effective duration (yrs)": r"Effective\|Duration\|([\d.]+) yrs\|as of\|([A-Za-z]{3} \d\d, \d{4})",
          "Convexity (/100)": r"Convexity\|(-?[\d.]+)\|as of\|([A-Za-z]{3} \d\d, \d{4})",
          "Option adjusted spread (bp)": r"Option Adjusted\|Spread\|(-?[\d.]+) bps\|as of\|([A-Za-z]{3} \d\d, \d{4})",
          "Average yield to maturity (%)": r"Average Yield to\|Maturity\|(-?[\d.]+)%\|as of\|([A-Za-z]{3} \d\d, \d{4})"}


def snapshot() -> pd.DataFrame:
    rows = {}
    for tk, url in PAGES.items():
        t = requests.get(url, headers=UA, timeout=60).text
        t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
        t = html.unescape(re.sub(r"<[^>]+>", "|", t))
        t = re.sub(r"\|[\s|]*", "|", t)
        row = {"Source": url, "Retrieved": str(date.today())}
        for k, pat in FIELDS.items():
            m = re.search(pat, t)
            row[k] = float(m.group(1)) if m else None
            row[k + " as of"] = m.group(2) if m else None
        rows[tk] = row
    return pd.DataFrame(rows).T
