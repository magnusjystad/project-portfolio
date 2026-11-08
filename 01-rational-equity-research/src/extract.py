"""Extract Rational's consolidated statements (current-year column) from each annual report.
All figures in thousands of euros, exactly as printed; each value is taken from the report for that year."""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

NUM = r"[−\-–]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|[−\-–](?=\s|$)"


def num(s):
    s = s.replace("−", "-").replace("–", "-").replace(",", "")
    if re.fullmatch(r"-?\d{1,3}\.\d{3}", s):     # a stray '.' used as thousands separator (e.g. '3.463')
        s = s.replace(".", "")
    return 0.0 if s == "-" else float(s)


TOKEN = r"(?:[−\-–]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|[−\-–])"


def ncols_of(text):
    """Number of value columns, from the header line with the period labels (2 or 3)."""
    for line in text.splitlines():
        if re.search(r"(Notes?|in kEUR|in thousands of euros).*(20\d\d|019)", line):
            n = len(re.findall(r"(?:31 Dec|1 Jan)\s+(?:20\d\d|019)|\b20\d\d\b", line))
            if n >= 2:
                return min(n, 3)
    return 2


def lines_with_numbers(text):
    """Yield (section, label, current, prior) for lines ending in the period columns."""
    ncols = ncols_of(text)
    section = None
    for raw in text.splitlines():
        line = raw.replace("\u00ad", "-").replace("restated1", "").strip()
        for pat, sec in [(r"^Non-current assets", "nca"), (r"^Current assets", "ca"), (r"^Equity\b", "eq"),
                         (r"^Non-current liabilities", "ncl"), (r"^Current liabilities", "cl")]:
            if re.match(pat, line):
                section = sec
        toks = line.split()
        vals = []
        while toks and re.fullmatch(TOKEN, toks[-1]) and len(vals) < ncols:
            vals.insert(0, toks.pop())
        if len(vals) < ncols:
            continue
        label = " ".join(toks)
        label = re.sub(r"(\s+\d{1,2}(\s*,\s*\d{1,2})*,?)+$", "", label).strip()
        if not re.search(r"[A-Za-z]", label):
            continue
        yield section, label, num(vals[0]), num(vals[1])


IS_MAP = [("Sales revenues", r"^Sales revenues"), ("Cost of sales", r"^Cost of sales"), ("Gross profit", r"^Gross profit"),
          ("Sales and service expenses", r"^Sales and service"), ("R&D expenses", r"^Research and development"),
          ("G&A expenses", r"^General administration"), ("Other operating income", r"^Other operating income"),
          ("Other operating expenses", r"^Other operating expenses"), ("EBIT", r"^Earnings before (interest|financial result) and taxes"),
          ("Interest income", r"^Interest (and similar )?income"), ("Interest expenses", r"^Interest (and similar )?expenses"),
          ("Other financial result", r"^Other financial result"), ("IAS 29 result", r"^Gain or loss on the net monetary"),
          ("EBT", r"^Earnings before taxes"), ("Income taxes", r"^Income taxes"), ("Net profit", r"^Profit or loss after taxes")]
BS_MAP = [("Non-current assets", None, r"^Non-current assets"), ("Intangible assets", "nca", r"^Intangible assets"),
          ("PP&E", "nca", r"^Property, plant and equipment"), ("Non-current financial assets", "nca", r"^(Other )?[Ff]inancial assets"),
          ("Deferred tax assets", "nca", r"^Deferred tax assets"), ("Current assets", None, r"^Current assets"),
          ("Inventories", "ca", r"^Inventories"), ("Trade receivables", "ca", r"^Trade (accounts )?receivable"),
          ("Fixed deposits > 3 months", "ca", r"^Deposits( with maturities|$|\s+\d)"),
          ("Other current financial assets", "ca", r"^Other (current )?financial assets"),
          ("Cash", "ca", r"^Cash and cash equivalents"), ("Total assets", None, r"^Total assets"),
          ("Equity", None, r"^Equity$|^Equity \d|^Equity"), ("Pensions", "ncl", r"^(Pension|Provisions for pensions)"),
          ("Non-current liabilities", None, r"^Non-current liabilities"),
          ("Bank debt (non-current)", "ncl", r"^(Non.current liabilities to banks|Financial debt)"),
          ("Other financial liabilities (non-current)", "ncl", r"^Other (non-current )?financial liabilities"),
          ("Current liabilities", None, r"^Current liabilities"), ("Bank debt (current)", "cl", r"^(Current liabilities to banks|Financial debt)"),
          ("Trade payables", "cl", r"^Trade accounts payable"),
          ("Other financial liabilities (current)", "cl", r"^Other (current )?financial liabilities"),
          ("Total equity and liabilities", None, r"^Total equity and liabilities")]
CF_MAP = [("CF EBT", r"^Earnings before taxes"), ("D&A", r"^Depreciation and amortisation"),
          ("Chg inventories", r"^Inventories"), ("Chg receivables", r"^Trade accounts receivable"),
          ("Chg provisions", r"^Provisions"), ("Chg payables", r"^Trade accounts payable"),
          ("Income taxes paid", r"^Income taxes paid"), ("CFO", r"^Cash flow from operating activities"),
          ("Capex", r"^(Capital expenditures|Investments) in intangible"), ("CFI", r"^Cash flow from investing activities"),
          ("Dividends paid", r"^Dividends paid"), ("Lease payments", r"^(Payments for|Repayment of) lease"),
          ("CFF", r"^Cash flow from financing activities"), ("Cash start", r"^Cash and cash equivalents as at 1"),
          ("Cash end", r"^Cash and cash equivalents as at 31")]


def page_texts(p):
    w = p.width
    return {"full": p.extract_text() or "", "left": p.crop((0, 0, w / 2, p.height)).extract_text() or "",
            "right": p.crop((w / 2, 0, w, p.height)).extract_text() or ""}


TITLES = {"IS": r"Statement of Comprehensive Income\s*\n\s*RATIONAL Group",
          "BS": r"Balance Sheet\s*\n\s*RATIONAL Group",
          "CF": r"Cash [Ff]low [Ss]tatement\s*\n\s*RATIONAL Group"}


def find_statement_texts(pdf):
    """Return {statement: (page number, text)}; for side-by-side layouts the relevant half page."""
    found = {}
    for i, p in enumerate(pdf.pages):
        t = p.extract_text() or ""
        if not re.search(r"RATIONAL Group", t):
            continue
        halves = page_texts(p) if re.search(r"RATIONAL Group\s+RATIONAL Group", t) else None
        for k, pat in TITLES.items():
            if k in found:
                continue
            if halves is not None:
                for side in ("left", "right"):
                    if re.search(pat, halves[side]):
                        found[k] = (i + 1, halves[side])
                continue
            if re.search(pat, t):
                found[k] = (i + 1, t)
            elif re.search(pat.replace("\\s*\\n\\s*RATIONAL Group", ""), t):
                halves = halves or page_texts(p)
                for side in ("left", "right"):
                    if re.search(pat, halves[side]):
                        found[k] = (i + 1, halves[side])
    return found


def extract_year(path: Path):
    out, pages = {}, {}
    with pdfplumber.open(path) as pdf:
        st = find_statement_texts(pdf)
        pages = {k: v[0] for k, v in st.items()}
        if "IS" in st:
            for sec, lab, cur, pri in lines_with_numbers(st["IS"][1]):
                for key, pat in IS_MAP:
                    if re.search(pat, lab) and key not in out:
                        out[key] = cur
                        break
        if "BS" in st:
            pgno, t = st["BS"]
            if "Total equity and liabilities" not in t.split("Equity and liabilities")[-1]:
                nxt = pdf.pages[pgno]
                t += "\n" + (nxt.extract_text() or "")
            first_total = True
            for sec, lab, cur, pri in lines_with_numbers(t):
                if re.match(r"^Total (assets|equity and liabilities)", lab):
                    key = "Total assets" if first_total else "Total equity and liabilities"
                    first_total = False
                    out.setdefault(key, cur)
                    continue
                for key, s_req, pat in BS_MAP:
                    if re.search(pat, lab) and (s_req is None or s_req == sec) and key not in out:
                        out[key] = cur
                        break
        if "CF" in st:
            for sec, lab, cur, pri in lines_with_numbers(st["CF"][1]):
                for key, pat in CF_MAP:
                    if re.search(pat, lab) and key not in out:
                        out[key] = cur
                        break
    out["_pages"] = pages
    return out
