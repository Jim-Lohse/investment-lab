# Demand-signal snapshot: Taiwan monthly revenue + Korea exports + Japan + U.S. trade

_Generated 2026-10-29 by `signals/compute_signals.py`._
_Derived data; the underlying records in `data/` are the source of truth._

## Taiwan monthly revenue — 2026-09

| Group | n | Agg YoY % | Median YoY % | Breadth % |
|---|---:|---:|---:|---:|
| ai_compute | 5 | 49.72 | 97.78 | 100.0 |
| ai_server_odm | 5 | 55.74 | 76.69 | 100.0 |
| power_cooling | 5 | 20.40 | 16.54 | 100.0 |
| robotics_motion | 3 | 27.99 | 26.60 | 100.0 |
| network_interconnect | 3 | 57.54 | 39.16 | 100.0 |
| photonics_epi | 2 | 85.63 | 109.82 | 100.0 |
| photonics_cpo | 8 | 62.33 | 68.60 | 100.0 |
| all_listed | 1973 | 43.54 | 14.18 | 71.2 |

_2026-08 ai_compute agg YoY: 54.13%_

_2026-07 ai_compute agg YoY: 42.67%_

## Korea trade (KCS)

| Period | Window | Item | USD k | YoY % |
|---|---|---|---:|---:|
| 2026-10 | D20 | exp:중국 | 16685883 | 154.35 |
| 2026-10 | D20 | exp:철강제품 | 2588031 | 42.61 |
| 2026-10 | D20 | exp:컴퓨터주변기기 | 2431846 | 424.00 |
| 2026-10 | D20 | exp:홍콩 | 2282906 | 98.82 |
| 2026-10 | D20 | imp:TOTAL | 47116652 | 42.83 |
| 2026-10 | D20 | imp:가스 | 2820165 | 112.37 |
| 2026-10 | D20 | imp:기계류 | 1920164 | 43.68 |
| 2026-10 | D20 | imp:대만 | 3380646 | 84.18 |
| 2026-10 | D20 | imp:러시아 연방 | 628316 | 64.79 |
| 2026-10 | D20 | imp:말레이시아 | 1300827 | 64.49 |
| 2026-10 | D20 | imp:무선통신기기 | 771668 | 43.10 |
| 2026-10 | D20 | imp:미국 | 4672059 | 12.94 |
| 2026-10 | D20 | imp:반도체 | 7573283 | 78.44 |
| 2026-10 | D20 | imp:반도체제조용장비 | 1847366 | 93.44 |
| 2026-10 | D20 | imp:베트남 | 2222164 | 27.86 |
| 2026-10 | D20 | imp:사우디아라비아 | 2270514 | 32.51 |
| 2026-10 | D20 | imp:석유제품 | 1430695 | 31.33 |
| 2026-10 | D20 | imp:석탄 | 720308 | 16.05 |
| 2026-10 | D20 | imp:승용차 | 713120 | 10.55 |
| 2026-10 | D20 | imp:원유 | 7448489 | 42.92 |
| 2026-10 | D20 | imp:유럽연합 | 4086140 | 34.57 |
| 2026-10 | D20 | imp:일본 | 3351691 | 45.64 |
| 2026-10 | D20 | imp:정밀기기 | 1130015 | 24.39 |
| 2026-10 | D20 | imp:중국 | 11290244 | 71.12 |
| 2026-10 | D20 | imp:호주 | 2163269 | 7.36 |

## Japan trade (MOF / Customs) — supply side

_YoY in yen is what MOF publishes. YoY in USD restates the same series at the reference rate for that window; FX pt is the difference, the share of the published growth that is the currency rather than the trade._

| Period | Window | Source | Item | JPY m | YoY % (yen) | YoY % (USD) | FX pt | YoY % (MOF) |
|---|---|---|---|---:|---:|---:|---:|---:|
| 2026-09 | D20 | press_release | BAL:Grand Total | 27439 | -119.75 | -118.73 | -1.02 |  |
| 2026-09 | D20 | press_release | E:Grand Total | 7879504 | 23.35 | 16.94 | 6.41 | 23.50 |
| 2026-09 | D20 | press_release | I:Grand Total | 7852065 | 20.31 | 14.05 | 6.26 | 19.90 |
| 2026-09 | MONTH | press_release | BAL:Grand Total | -556479 | 134.45 | 121.76 | 12.69 | 100.40 |
| 2026-09 | MONTH | press_release | E:(IC) | 734423 | 55.51 | 47.09 | 8.42 | 55.50 |
| 2026-09 | MONTH | press_release | E:ELECTRICAL MEASURING | 216767 | 26.24 | 19.41 | 6.83 | 26.20 |
| 2026-09 | MONTH | press_release | E:Grand Total | 10953854 | 16.37 | 10.07 | 6.30 | 16.50 |
| 2026-09 | MONTH | press_release | E:SCIENTIFIC, OPTICAL INST | 242605 | 11.60 | 5.56 | 6.04 | 11.60 |
| 2026-09 | MONTH | press_release | E:SEMICON MACHINERY ETC | 553333 | 43.94 | 36.15 | 7.79 | 43.90 |
| 2026-09 | MONTH | press_release | E:SEMICONDUCTORS ETC | 933636 | 49.43 | 41.35 | 8.08 | 49.40 |
| 2026-09 | MONTH | press_release | E:TELEPHONY, TELEGRAPHY | 33823 | 22.77 | 16.13 | 6.64 | 22.80 |
| 2026-09 | MONTH | press_release | I:(IC) | 550090 | 61.44 | 52.70 | 8.74 | 61.40 |
| 2026-09 | MONTH | press_release | I:ELECTRICAL MEASURING | 101844 | -0.22 | -5.62 | 5.40 | -0.30 |
| 2026-09 | MONTH | press_release | I:Grand Total | 11510333 | 19.27 | 12.82 | 6.45 | 18.90 |
| 2026-09 | MONTH | press_release | I:SCIENTIFIC, OPTICAL INST | 223883 | 2.18 | -3.35 | 5.53 | 1.90 |
| 2026-09 | MONTH | press_release | I:SEMICONDUCTORS ETC | 605250 | 51.45 | 43.25 | 8.20 | 51.40 |
| 2026-09 | MONTH | press_release | I:TELEPHONY, TELEGRAPHY | 507335 | 6.82 | 1.04 | 5.78 | 6.70 |
| 2026-10 | D10 | press_release | BAL:Grand Total | -339857 | -37.84 | -41.02 | 3.18 | -41.10 |
| 2026-10 | D10 | press_release | E:Grand Total | 3822613 | 30.62 | 23.94 | 6.68 | 30.70 |
| 2026-10 | D10 | press_release | I:Grand Total | 4162470 | 19.84 | 13.72 | 6.12 | 18.90 |
| 2026-09 | MONTH | timeseries:world_exports_by_commodity | E:半導体等製造装置 | 553333 | 43.95 | 36.16 | 7.79 |  |
| 2026-09 | MONTH | timeseries:world_exports_by_commodity | E:半導体等電子部品 | 933636 | 49.43 | 41.35 | 8.08 |  |
| 2026-09 | MONTH | timeseries:world_exports_by_commodity | E:科学光学機器 | 242605 | 11.60 | 5.56 | 6.04 |  |
| 2026-09 | MONTH | timeseries:world_exports_by_commodity | E:総額 | 10953854 | 16.47 | 10.17 | 6.30 |  |
| 2026-09 | MONTH | timeseries:world_imports_by_commodity | I:半導体等電子部品 | 605250 | 51.44 | 43.25 | 8.19 |  |
| 2026-09 | MONTH | timeseries:world_imports_by_commodity | I:科学光学機器 | 223883 | 1.90 | -3.62 | 5.52 |  |
| 2026-09 | MONTH | timeseries:world_imports_by_commodity | I:総額 | 11510333 | 18.88 | 12.44 | 6.44 |  |
| 2026-09 | MONTH | estat_hs:DETAILED | E:HS280461 | 3344 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:DETAILED | E:HS3818 | 66958 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:DETAILED | E:HS8486 | 553333 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:DETAILED | E:HS8517 | 27639 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:DETAILED | E:HS8541 | 143284 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:DETAILED | E:HS8542 | 786883 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:DETAILED | E:HS854470 | 5491 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:DETAILED | E:HS9001 | 39733 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:DETAILED | E:HS9013 | 9722 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:PROV9 | I:HS280461 | 6459 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:PROV9 | I:HS3818 | 18714 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:PROV9 | I:HS8486 | 107524 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:PROV9 | I:HS8517 | 484916 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:PROV9 | I:HS8541 | 48895 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:PROV9 | I:HS8542 | 554179 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:PROV9 | I:HS854470 | 2642 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:PROV9 | I:HS9001 | 35065 |  |  |  |  |
| 2026-09 | MONTH | estat_hs:PROV9 | I:HS9013 | 12610 |  |  |  |  |

_Reference rate, newest window stored: 158.10 yen per USD (2026-10)._

## U.S. trade by HTS code (Census) — demand side

| Period | I/E | Code | Country | USD k | YoY % | Share of code % |
|---|---|---|---|---:|---:|---:|
| 2026-08 | I | 381800 | TAIWAN | 81084 | 311.83 | 29.2 |
| 2026-08 | I | 381800 | JAPAN | 74490 | 23.42 | 26.8 |
| 2026-08 | I | 381800 | LAOS | 44942 |  | 16.2 |
| 2026-08 | I | 381800 | KOREA, SOUTH | 20231 | -8.75 | 7.3 |
| 2026-08 | I | 381800 | GERMANY | 11013 | 16.11 | 4.0 |
| 2026-08 | I | 381800 | FRANCE | 10269 | -1.86 | 3.7 |
| 2026-08 | I | 848620 | NETHERLANDS | 520238 | 147.07 | 41.8 |
| 2026-08 | I | 848620 | JAPAN | 225965 | 155.67 | 18.2 |
| 2026-08 | I | 848620 | CHINA | 162049 | 862.96 | 13.0 |
| 2026-08 | I | 848620 | MALAYSIA | 103988 | 101.79 | 8.4 |
| 2026-08 | I | 848620 | KOREA, SOUTH | 83159 | 226.32 | 6.7 |
| 2026-08 | I | 848620 | SINGAPORE | 44667 | -46.55 | 3.6 |
| 2026-08 | I | 8517620090 | THAILAND | 2467468 | 145.36 | 36.7 |
| 2026-08 | I | 8517620090 | VIETNAM | 1229078 | 93.21 | 18.3 |
| 2026-08 | I | 8517620090 | TAIWAN | 950240 | 110.07 | 14.1 |
| 2026-08 | I | 8517620090 | MALAYSIA | 647601 | 80.84 | 9.6 |
| 2026-08 | I | 8517620090 | MEXICO | 482476 | -4.98 | 7.2 |
| 2026-08 | I | 8517620090 | CHINA | 395896 | -2.79 | 5.9 |
| 2026-08 | I | 854141 | CHINA | 12331 | 2.98 | 21.7 |
| 2026-08 | I | 854141 | JAPAN | 11359 | -1.54 | 20.0 |
| 2026-08 | I | 854141 | GERMANY | 7855 | 112.34 | 13.8 |
| 2026-08 | I | 854141 | MALAYSIA | 7366 | -33.31 | 12.9 |
| 2026-08 | I | 854141 | TAIWAN | 6061 | -2.15 | 10.6 |
| 2026-08 | I | 854141 | THAILAND | 4152 | 79.37 | 7.3 |
| 2026-08 | E | 381800 | MALAYSIA | 24879 | -28.78 | 17.3 |
| 2026-08 | E | 381800 | TAIWAN | 24663 | 32.31 | 17.2 |
| 2026-08 | E | 381800 | OMAN | 16874 |  | 11.8 |
| 2026-08 | E | 381800 | JAPAN | 13209 | -27.11 | 9.2 |
| 2026-08 | E | 381800 | SINGAPORE | 12498 | 14.01 | 8.7 |
| 2026-08 | E | 381800 | CHINA | 11704 | -10.03 | 8.2 |
| 2026-08 | E | 848620 | KOREA, SOUTH | 244726 | 120.02 | 28.3 |
| 2026-08 | E | 848620 | TAIWAN | 213149 | 23.14 | 24.7 |
| 2026-08 | E | 848620 | IRELAND | 106968 | 630.22 | 12.4 |
| 2026-08 | E | 848620 | SINGAPORE | 100472 | 5.20 | 11.6 |
| 2026-08 | E | 848620 | CHINA | 52372 | -51.54 | 6.1 |
| 2026-08 | E | 848620 | JAPAN | 50363 | -31.94 | 5.8 |
| 2026-08 | E | 854141 | GERMANY | 17147 | -5.87 | 19.7 |
| 2026-08 | E | 854141 | HONG KONG | 11658 | 6.07 | 13.4 |
| 2026-08 | E | 854141 | THAILAND | 11538 | 184.04 | 13.2 |
| 2026-08 | E | 854141 | MEXICO | 10765 | -17.14 | 12.4 |
| 2026-08 | E | 854141 | MALAYSIA | 6907 | 191.41 | 7.9 |
| 2026-08 | E | 854141 | CHINA | 5646 | -45.09 | 6.5 |
| 2026-08 | E | 381800 | ALL COUNTRIES | 143455 | 1.00 | 100.0 |
| 2026-08 | E | 848620 | ALL COUNTRIES | 864376 | 32.77 | 100.0 |
| 2026-08 | E | 851762 | ALL COUNTRIES | 2800140 | 30.68 | 100.0 |
| 2026-08 | E | 854141 | ALL COUNTRIES | 87115 | -0.97 | 100.0 |
| 2026-08 | E | 854149 | ALL COUNTRIES | 95228 | 44.69 | 100.0 |
| 2026-08 | I | 280461 | ALL COUNTRIES | 47407 | 205.27 | 100.0 |
| 2026-08 | I | 381800 | ALL COUNTRIES | 277690 | 95.90 | 100.0 |
| 2026-08 | I | 848610 | ALL COUNTRIES | 227762 | 591.30 | 100.0 |
| 2026-08 | I | 848620 | ALL COUNTRIES | 1243684 | 117.41 | 100.0 |
| 2026-08 | I | 848640 | ALL COUNTRIES | 147523 | 65.79 | 100.0 |
| 2026-08 | I | 848690 | ALL COUNTRIES | 646523 | 95.21 | 100.0 |
| 2026-08 | I | 851762 | ALL COUNTRIES | 12194411 | 90.10 | 100.0 |
| 2026-08 | I | 8517620090 | ALL COUNTRIES | 6728089 | 75.76 | 100.0 |
| 2026-08 | I | 851779 | ALL COUNTRIES | 230956 | 21.46 | 100.0 |
| 2026-08 | I | 854110 | ALL COUNTRIES | 49938 | 35.13 | 100.0 |
| 2026-08 | I | 854141 | ALL COUNTRIES | 56918 | 7.41 | 100.0 |
| 2026-08 | I | 854149 | ALL COUNTRIES | 78152 | -14.15 | 100.0 |
| 2026-08 | I | 854470 | ALL COUNTRIES | 661404 | 88.81 | 100.0 |
| 2026-08 | I | 900110 | ALL COUNTRIES | 64453 | 224.30 | 100.0 |
| 2026-08 | I | 901320 | ALL COUNTRIES | 92426 | 20.94 | 100.0 |
| 2026-08 | I | 901380 | ALL COUNTRIES | 117853 | 9.34 | 100.0 |

---
Validation status (constitution §21): raw government data, mechanically aggregated. Tier 1 screening input only; not a thesis, not advice.
