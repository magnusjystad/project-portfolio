"""Grifols credit metrics 2019 – LTM June 2026 -> data/credit_history.csv

Two kinds of inputs:
1. IFRS line items from SEC XBRL company facts (20-F, 2019–2024; the latest filing wins, so restatements are used) and,
   for 2025 (not yet in XBRL), the audited 2025 statements in the 6-K of 26 Feb 2026.
2. Company-defined metrics that are not XBRL-tagged (Adjusted EBITDA as per the Credit Agreement, net financial debt as per
   the Credit Agreement, leverage ratios, liquidity). These are transcribed from the results releases listed in SOURCES;
   each value can be found in the table cited.

    python src/history.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "source"
YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]

XBRL = {"Revenue": "Revenue", "EBIT": "ProfitLossFromOperatingActivities", "D&A": "DepreciationAndAmortisationExpense",
        "Cash": "CashAndCashEquivalents", "Non-current financial liabilities": "NoncurrentFinancialLiabilities",
        "Current financial liabilities": "CurrentFinancialLiabilities", "Interest paid": "InterestPaidClassifiedAsOperatingActivities",
        "Operating cash flow": "CashFlowsFromUsedInOperatingActivities", "Capex PP&E": "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
        "Capex intangibles": "PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities", "Lease payments": "PaymentsOfLeaseLiabilitiesClassifiedAsFinancingActivities"}
# FY2025 audited statements (6-K 26 Feb 2026, consolidated statements of cash flows / balance sheet / leverage annex)
FY2025 = {"Revenue": 7524, "EBIT": 1243, "D&A": 450, "Cash": 825, "Non-current financial liabilities": 9091,
          "Current financial liabilities": 552, "Interest paid": 532, "Operating cash flow": 1047, "Capex PP&E": 265,
          "Capex intangibles": 158, "Lease payments": 119}
# H1 2026 (6-K 28 Jul 2026): balance sheet at 30 June 2026 and LTM Q2'26 annex tables
# Flows are LTM = FY2025 + H1 2026 − H1 2025 (H1 cash flow statement: interest paid 271 / 297, CFO 337 / 293, PP&E 118 / 109,
# PP&E + intangibles 209 / 182, leases 60 / 61; revenue 3,574 / 3,677)
LTM_JUN26 = {"Revenue": 7524 + 3574 - 3677, "EBIT": 1202, "D&A": 443, "Cash": 513, "Non-current financial liabilities": 8808,
             "Current financial liabilities": 548, "Interest paid": 532 + 271 - 297, "Operating cash flow": 1047 + 337 - 293,
             "Capex PP&E": 265 + 118 - 109, "Capex intangibles": 158 + (209 - 118) - (182 - 109), "Lease payments": 119 + 60 - 61}

COMPANY = {  # Adjusted EBITDA (credit-agreement basis, excl. IFRS 16), net financial debt (credit-agreement basis), leverage
    2019: (1373.3, 5724.9, 4.17, "FY2019 results release (6-K 27 Feb 2020): net financial debt, EBITDA adjusted 12M, net leverage ratio"),
    2020: (1263.9, 5713.7, 4.52, "FY2020 results release (6-K 26 Feb 2021), same table"),
    2021: (1076.8, 5828.0, 5.41, "FY2021 results release (6-K 28 Feb 2022), same table"),
    2022: (1287.0, 9191.0, 7.1, "FY2023 results (6-K 29 Feb 2024): leverage ratio as per Credit Agreement incl. Biotest, FY2022 column"),
    2023: (1471.0, 9416.0, 6.4, "FY2024 results (6-K 26 Feb 2025): leverage ratio as per Credit Agreement, FY2023 column (restated)"),
    2024: (1753.0, 8046.0, 4.6, "FY2024 results (6-K 26 Feb 2025): leverage ratio as per Credit Agreement, Q4'24"),
    2025: (1852.0, 7759.0, 4.2, "FY2025 results (6-K 26 Feb 2026): leverage ratio as per Credit Agreement, Q4'25"),
    "LTM Jun-26": (1863.0, 7798.0, 4.2, "H1 2026 results (6-K 28 Jul 2026): leverage ratio as per Credit Agreement, LTM Q2'26"),
}
SECURED = {  # net secured debt and ratio as per Credit Agreement, where disclosed
    2024: (5239.0, 2.7), 2025: (4789.0, 2.6), "LTM Jun-26": (4939.0, 2.7)}
LIQUIDITY = {2024: 1860.0, "LTM Jun-26": 2030.0}       # company-stated liquidity (cash + available committed facilities)
FCF_COMPANY = {2024: 267.0, 2025: 468.0}                 # free cash flow pre-M&A (company definition)


def xbrl():
    d = json.load(open(SRC / "grifols_companyfacts.json"))["facts"]["ifrs-full"]
    out = {}
    for name, concept in XBRL.items():
        u = list(d[concept]["units"].values())[0]
        rows = [x for x in u if x.get("form") == "20-F" and x["end"].endswith("12-31")
                and (x.get("start") is None or x["start"][5:] == "01-01")]
        rows.sort(key=lambda x: x["filed"])
        out[name] = {}
        for x in rows:                      # later filings overwrite earlier ones (restatements)
            y = int(x["end"][:4])
            if y in YEARS:
                out[name][y] = x["val"] / 1e6
    return pd.DataFrame(out).T


def build():
    X = xbrl()
    X[2025] = pd.Series(FY2025)
    X["LTM Jun-26"] = pd.Series(LTM_JUN26)
    H = X.reindex(columns=YEARS + ["LTM Jun-26"])
    H.loc["Reported EBITDA"] = H.loc["EBIT"] + H.loc["D&A"]
    H.loc["Gross financial debt (incl. leases)"] = H.loc["Non-current financial liabilities"] + H.loc["Current financial liabilities"]
    H.loc["Net financial debt (balance sheet)"] = H.loc["Gross financial debt (incl. leases)"] - H.loc["Cash"]
    H.loc["Net leverage, reported (x)"] = H.loc["Net financial debt (balance sheet)"] / H.loc["Reported EBITDA"]
    for k, (e, nd, lev, src) in COMPANY.items():
        H.loc["Adjusted EBITDA (Credit Agreement)", k] = e
        H.loc["Net financial debt (Credit Agreement)", k] = nd
        H.loc["Net leverage, Credit Agreement (x)", k] = lev
    H.loc["Adjusted EBITDA / cash interest (x)"] = H.loc["Adjusted EBITDA (Credit Agreement)"] / H.loc["Interest paid"]
    H.loc["FCF (CFO − capex − leases)"] = H.loc["Operating cash flow"] - H.loc["Capex PP&E"] - H.loc["Capex intangibles"] - H.loc["Lease payments"]
    H.loc["FCF / gross debt"] = H.loc["FCF (CFO − capex − leases)"] / H.loc["Gross financial debt (incl. leases)"]
    for k, (nsd, r) in SECURED.items():
        H.loc["Net secured debt (Credit Agreement)", k] = nsd
        H.loc["Net secured leverage, Credit Agreement (x)", k] = r
    for k, v in LIQUIDITY.items():
        H.loc["Liquidity (company)", k] = v
    for k, v in FCF_COMPANY.items():
        H.loc["FCF pre-M&A (company definition)", k] = v
    H.columns = [str(c) for c in H.columns]
    H.to_csv(ROOT / "data" / "credit_history.csv")
    pd.DataFrame([{"period": k, "source": v[3]} for k, v in COMPANY.items()]).to_csv(ROOT / "data" / "credit_history_sources.csv", index=False)
    return H


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    print(build().round(2).to_string())
