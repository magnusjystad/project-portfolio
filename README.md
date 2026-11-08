# Investment Research Portfolio

Asset management projects built on real, public data, one folder per project. Each folder holds
`/data` (every input and result as CSV), `/notebooks` (the analysis), `/report` (the PDF and charts)
and a README with the same seven headings: Question, Answer, Data, Method, Results, Limitations, How to run.

No number in this repository is made up or simulated as data: every input is downloaded from the source
named in the project README and saved in `data/`, and every report is generated from the notebook's outputs.

| # | Project | Answer in one line |
|---|---|---|
| 01 | [Equity research initiation: Rational AG](01-rational-equity-research) | Sell: probability-weighted DCF target €414, 27% below €566.50 (cost of equity 9.79%). Excel model with live formulas. |
| 02 | [Reverse DCF: is Rheinmetall priced for perfection?](02-rheinmetall-reverse-dcf) | No: at a 5.9% WACC the €926 price implies 4.0% sales growth a year to 2035, below our bear case on budget, backlog and margin tests → Buy. |
| 03 | [High-yield credit memo: Grifols secured vs. unsecured](03-grifols-credit-memo) | Overweight the 3.875% unsecured 2028s: 200 bp more expected return than the 7.125% secured 2030s (both recover 100% at 6.0x; the secured notes are priced to their 2027 call). |
| 04 | [Strategic asset allocation and IPS: Northbridge University Endowment](04-northbridge-saa-ips) | Growth allocation: 55% probability of preserving real value over 20 years; concentrated in REITs (40%). |
| 05 | [Does optimization beat 1/N?](05-optimization-vs-1n) | Naive max-Sharpe beat 1/N after costs (Sharpe 0.80 vs 0.45), but not robustly; 60/40 beat everything (0.83). |
| 06 | [Factor premia since 1963, and do factor ETFs deliver them?](06-factor-premia) | Size is not significant since 1963, all five iShares factor ETFs load on their target, but QUAL and SIZE only 0.17× and 0.14×. |
| 07 | [Skill or exposure? Fidelity Contrafund attribution](07-contrafund-attribution) | Exposure: six-factor alpha 0.73% (t = 0.78); in 2025 selection was +529 bp, led by a private SpaceX stake. |
| 08 | [Manager selection: three global equity funds vs. the index](08-manager-selection) | ACWI: top-scoring active fund DODWX (85% active share) has a 10-year IR of −0.09, below the 0.2 hurdle. |
| 09 | [Risk dashboard for the Northbridge portfolio](09-northbridge-risk-dashboard) | 1-day 99% VaR $35.6m (1.78%); historical simulation best calibrated (41 exceptions vs 42 expected), GFC replay −38%. |
| 10 | [Yield curve model and bond portfolio scenario tool](10-yield-curve-scenarios) | A duration-matched barbell beats a 7y bullet by 268 bp in a bull flattener but gives up 18.5 bp of carry and roll-down. |
| 11 | [Text as data: replicating "Lazy Prices" on the S&P 100](11-lazy-prices) | Non-changers beat changers by 0.29% a month (t = 1.26; alpha 2.4% a year, t = 0.84): right direction, too few firms for significance, FinBERT and dictionary tone add nothing. |
| 12 | [Market stress tripwires: weekly check](12-stress-tripwires) | Bending, not breaking (7 Oct 2026): 0 of 17 tripwires fired, 4 near (JGB 30y, private credit defaults and redemptions, a life insurer downgrade), triggers set from each series' own history. |
| 13 | [Kvartalsrapport: gjenbrukbar investorrapport (PEF)](13-kvartalsrapport-mal) | Excel-mal + PDF-rapport for Q3 2026: 39 bygg, utleiegrad 97,3 %, IRR siden oppstart 7,8 % (rapportert), TVPI 1,52x; avstemt mot forvalters egne tall. |
| 14 | [Energi- og klimakartlegging av ti næringsbygg](14-energi-klima-portefolje) | Enova-attester mot EU-taksonomien og CRREM: 5 av 10 bygg (57 % av arealet) taksonomiforenlige; nivå 1-tiltak 2 519 MWh/år for NOK 30,3 mill. (14–16 år med 2025-pris, 9–10 år med 2026-pris). |
| 15 | [Investeringscase: Fugleåsen 7, Langhus](15-logistikk-investeringscase) | Logistikkbygg utleid til Norsk Lastbærer Pool: bud NOK 425 mill. (20 227 kr/m²), IRR 8,6 % ufinansiert / 10,6 % belånt mot krav 7,5 %; Excel-modell, memo og PowerPoint. |

## Setup
```bash
python -m pip install -r requirements.txt   # Python 3.12+
```
Shared code lives in `common/`: data loaders (`data.py`), chart style (`plotting.py`) and the PDF
report builder (`report.py`).
