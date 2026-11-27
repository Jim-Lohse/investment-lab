# Demand-signal snapshot: Taiwan monthly revenue + Korea exports + Japan + U.S. trade

_Generated 2026-11-27 by `signals/compute_signals.py`._
_Derived data; the underlying records in `data/` are the source of truth._

## Taiwan monthly revenue — 2026-10

| Group | n | Agg YoY % | Median YoY % | Breadth % |
|---|---:|---:|---:|---:|
| ai_compute | 5 | 55.69 | 126.96 | 100.0 |
| ai_server_odm | 5 | 64.73 | 80.94 | 100.0 |
| power_cooling | 5 | 30.03 | 30.12 | 80.0 |
| robotics_motion | 3 | 33.11 | 32.17 | 100.0 |
| network_interconnect | 3 | 84.22 | 79.99 | 100.0 |
| photonics_epi | 2 | 87.06 | 107.81 | 100.0 |
| photonics_cpo | 8 | 52.75 | 72.89 | 100.0 |
| all_listed | 1978 | 45.42 | 14.38 | 70.3 |

_2026-09 ai_compute agg YoY: 49.72%_

_2026-08 ai_compute agg YoY: 54.13%_

_2026-07 ai_compute agg YoY: 42.67%_

## Korea trade (KCS)

| Period | Window | Item | USD k | YoY % |
|---|---|---|---:|---:|
| 2026-11 | D20 | exp:중국 | 20044586 | 145.58 |
| 2026-11 | D20 | exp:철강제품 | 2857420 | 27.02 |
| 2026-11 | D20 | exp:컴퓨터주변기기 | 3665799 | 330.57 |
| 2026-11 | D20 | exp:홍콩 | 3098206 | 99.15 |
| 2026-11 | D20 | imp:TOTAL | 50288212 | 39.43 |
| 2026-11 | D20 | imp:가스 | 2537047 | 93.91 |
| 2026-11 | D20 | imp:기계류 | 1965817 | 13.76 |
| 2026-11 | D20 | imp:대만 | 3635968 | 81.49 |
| 2026-11 | D20 | imp:러시아 연방 | 532200 | 20.41 |
| 2026-11 | D20 | imp:말레이시아 | 1055076 | 21.99 |
| 2026-11 | D20 | imp:무선통신기기 | 531828 | -21.98 |
| 2026-11 | D20 | imp:미국 | 6266435 | 45.23 |
| 2026-11 | D20 | imp:반도체 | 9311182 | 103.39 |
| 2026-11 | D20 | imp:반도체제조용장비 | 2345326 | 48.61 |
| 2026-11 | D20 | imp:베트남 | 2330092 | 26.85 |
| 2026-11 | D20 | imp:사우디아라비아 | 2447972 | 148.74 |
| 2026-11 | D20 | imp:석유제품 | 1415016 | 40.87 |
| 2026-11 | D20 | imp:석탄 | 1078259 | 31.80 |
| 2026-11 | D20 | imp:승용차 | 963342 | 33.00 |
| 2026-11 | D20 | imp:원유 | 6832745 | 83.37 |
| 2026-11 | D20 | imp:유럽연합 | 4690094 | 17.04 |
| 2026-11 | D20 | imp:일본 | 3613029 | 27.04 |
| 2026-11 | D20 | imp:정밀기기 | 1186041 | 13.14 |
| 2026-11 | D20 | imp:중국 | 13065784 | 52.52 |
| 2026-11 | D20 | imp:호주 | 2060775 | -0.78 |

## Japan trade (MOF / Customs) — supply side

_YoY in yen is what MOF publishes. YoY in USD restates the same series at the reference rate for that window; FX pt is the difference, the share of the published growth that is the currency rather than the trade._

| Period | Window | Source | Item | JPY m | YoY % (yen) | YoY % (USD) | FX pt | YoY % (MOF) |
|---|---|---|---|---:|---:|---:|---:|---:|
| 2026-10 | D20 | press_release | BAL:Grand Total | -810433 | 163.44 | 150.85 | 12.59 | 274.10 |
| 2026-10 | D20 | press_release | E:Grand Total | 7314664 | 26.44 | 20.39 | 6.05 | 23.50 |
| 2026-10 | D20 | press_release | I:Grand Total | 8125097 | 33.36 | 26.98 | 6.38 | 32.40 |
| 2026-10 | MONTH | press_release | BAL:Grand Total | -480722 | 112.64 | 103.94 | 8.70 | 59.20 |
| 2026-10 | MONTH | press_release | E:(IC) | 708150 | 50.24 | 44.09 | 6.15 | 50.20 |
| 2026-10 | MONTH | press_release | E:ELECTRICAL MEASURING | 236451 | 31.30 | 25.92 | 5.38 | 31.30 |
| 2026-10 | MONTH | press_release | E:Grand Total | 11765501 | 20.47 | 15.54 | 4.93 | 20.50 |
| 2026-10 | MONTH | press_release | E:SCIENTIFIC, OPTICAL INST | 268287 | 20.98 | 16.03 | 4.95 | 21 |
| 2026-10 | MONTH | press_release | E:SEMICON MACHINERY ETC | 544155 | 49.68 | 43.55 | 6.13 | 49.70 |
| 2026-10 | MONTH | press_release | E:SEMICONDUCTORS ETC | 929565 | 49.68 | 43.55 | 6.13 | 49.70 |
| 2026-10 | MONTH | press_release | E:TELEPHONY, TELEGRAPHY | 38697 | 43.42 | 37.55 | 5.87 | 43.40 |
| 2026-10 | MONTH | press_release | I:(IC) | 521594 | 67.57 | 60.71 | 6.86 | 67.50 |
| 2026-10 | MONTH | press_release | I:ELECTRICAL MEASURING | 113291 | 7.78 | 3.36 | 4.42 | 7.70 |
| 2026-10 | MONTH | press_release | I:Grand Total | 12246223 | 22.56 | 17.54 | 5.02 | 21.60 |
| 2026-10 | MONTH | press_release | I:SCIENTIFIC, OPTICAL INST | 244310 | 11.00 | 6.46 | 4.54 | 10.80 |
| 2026-10 | MONTH | press_release | I:SEMICONDUCTORS ETC | 580332 | 60.03 | 53.48 | 6.55 | 60 |
| 2026-10 | MONTH | press_release | I:TELEPHONY, TELEGRAPHY | 546552 | -10.04 | -13.72 | 3.68 | -10 |
| 2026-11 | D10 | press_release | BAL:Grand Total | -541506 | 371.32 | 357.95 | 13.37 | 273.70 |
| 2026-11 | D10 | press_release | E:Grand Total | 3418332 | 20.05 | 16.64 | 3.41 | 20.20 |
| 2026-11 | D10 | press_release | I:Grand Total | 3959838 | 33.67 | 29.88 | 3.79 | 32.40 |
| 2026-10 | MONTH | timeseries:world_exports_by_commodity | E:半導体等製造装置 | 544155 | 49.68 | 43.55 | 6.13 |  |
| 2026-10 | MONTH | timeseries:world_exports_by_commodity | E:半導体等電子部品 | 929565 | 49.68 | 43.55 | 6.13 |  |
| 2026-10 | MONTH | timeseries:world_exports_by_commodity | E:科学光学機器 | 268287 | 20.98 | 16.03 | 4.95 |  |
| 2026-10 | MONTH | timeseries:world_exports_by_commodity | E:総額 | 11765501 | 20.47 | 15.54 | 4.93 |  |
| 2026-10 | MONTH | timeseries:world_imports_by_commodity | I:半導体等電子部品 | 580332 | 60.03 | 53.47 | 6.56 |  |
| 2026-10 | MONTH | timeseries:world_imports_by_commodity | I:科学光学機器 | 244310 | 10.85 | 6.31 | 4.54 |  |
| 2026-10 | MONTH | timeseries:world_imports_by_commodity | I:総額 | 12246223 | 22.35 | 17.34 | 5.01 |  |
| 2026-10 | MONTH | estat_hs:DETAILED | E:HS280461 | 3735 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:DETAILED | E:HS3818 | 75518 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:DETAILED | E:HS8486 | 544155 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:DETAILED | E:HS8517 | 32259 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:DETAILED | E:HS8541 | 155440 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:DETAILED | E:HS8542 | 770772 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:DETAILED | E:HS854470 | 12484 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:DETAILED | E:HS9001 | 36357 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:DETAILED | E:HS9013 | 11445 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:PROV9 | I:HS280461 | 17724 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:PROV9 | I:HS3818 | 17808 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:PROV9 | I:HS8486 | 110287 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:PROV9 | I:HS8517 | 521406 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:PROV9 | I:HS8541 | 50980 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:PROV9 | I:HS8542 | 526290 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:PROV9 | I:HS854470 | 3964 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:PROV9 | I:HS9001 | 34295 |  |  |  |  |
| 2026-10 | MONTH | estat_hs:PROV9 | I:HS9013 | 14495 |  |  |  |  |

_Reference rate, newest window stored: 158.19 yen per USD (2026-11)._

## U.S. trade by HTS code (Census) — demand side

| Period | I/E | Code | Country | USD k | YoY % | Share of code % |
|---|---|---|---|---:|---:|---:|
| 2026-09 | I | 381800 | TAIWAN | 65297 | 277.97 | 29.3 |
| 2026-09 | I | 381800 | JAPAN | 65148 | -7.94 | 29.3 |
| 2026-09 | I | 381800 | KOREA, SOUTH | 21809 | 27.15 | 9.8 |
| 2026-09 | I | 381800 | LAOS | 18550 | 1161.93 | 8.3 |
| 2026-09 | I | 381800 | GERMANY | 10701 | 1.96 | 4.8 |
| 2026-09 | I | 381800 | FRANCE | 7077 | 855.03 | 3.2 |
| 2026-09 | I | 848620 | NETHERLANDS | 523196 | 626.72 | 34.6 |
| 2026-09 | I | 848620 | JAPAN | 309806 | 186.44 | 20.5 |
| 2026-09 | I | 848620 | CHINA | 190476 | 1078.79 | 12.6 |
| 2026-09 | I | 848620 | MALAYSIA | 143318 | 271.73 | 9.5 |
| 2026-09 | I | 848620 | SINGAPORE | 110129 | 157.40 | 7.3 |
| 2026-09 | I | 848620 | KOREA, SOUTH | 98507 | 213.97 | 6.5 |
| 2026-09 | I | 8517620090 | THAILAND | 2643050 | 102.81 | 33.0 |
| 2026-09 | I | 8517620090 | VIETNAM | 1826468 | 34.90 | 22.8 |
| 2026-09 | I | 8517620090 | TAIWAN | 1241053 | 144.51 | 15.5 |
| 2026-09 | I | 8517620090 | MALAYSIA | 771161 | 81.07 | 9.6 |
| 2026-09 | I | 8517620090 | MEXICO | 602494 | 7.07 | 7.5 |
| 2026-09 | I | 8517620090 | CHINA | 346905 | -13.51 | 4.3 |
| 2026-09 | I | 854141 | JAPAN | 12940 | 21.52 | 25.4 |
| 2026-09 | I | 854141 | CHINA | 8753 | 6.89 | 17.1 |
| 2026-09 | I | 854141 | GERMANY | 6536 | 74.95 | 12.8 |
| 2026-09 | I | 854141 | MALAYSIA | 6133 | -41.52 | 12.0 |
| 2026-09 | I | 854141 | TAIWAN | 4642 | 6.40 | 9.1 |
| 2026-09 | I | 854141 | THAILAND | 4025 | 60.32 | 7.9 |
| 2026-09 | E | 381800 | TAIWAN | 23524 | 15.27 | 15.6 |
| 2026-09 | E | 381800 | MALAYSIA | 22797 | -41.51 | 15.1 |
| 2026-09 | E | 381800 | KOREA, SOUTH | 17712 | 36.60 | 11.8 |
| 2026-09 | E | 381800 | JAPAN | 17268 | -19.23 | 11.5 |
| 2026-09 | E | 381800 | SINGAPORE | 13167 | 1.51 | 8.7 |
| 2026-09 | E | 381800 | CHINA | 9089 | -9.64 | 6.0 |
| 2026-09 | E | 848620 | TAIWAN | 313704 | 8.40 | 32.7 |
| 2026-09 | E | 848620 | KOREA, SOUTH | 232445 | 23.20 | 24.2 |
| 2026-09 | E | 848620 | SINGAPORE | 97438 | -3.97 | 10.2 |
| 2026-09 | E | 848620 | IRELAND | 81328 | 789.91 | 8.5 |
| 2026-09 | E | 848620 | JAPAN | 78065 | 95.36 | 8.1 |
| 2026-09 | E | 848620 | CHINA | 31813 | -39.15 | 3.3 |
| 2026-09 | E | 854141 | HONG KONG | 12177 | 27.72 | 14.0 |
| 2026-09 | E | 854141 | THAILAND | 12164 | 348.23 | 14.0 |
| 2026-09 | E | 854141 | GERMANY | 11702 | -29.94 | 13.5 |
| 2026-09 | E | 854141 | MEXICO | 11463 | -9.28 | 13.2 |
| 2026-09 | E | 854141 | CHINA | 7264 | 6.38 | 8.4 |
| 2026-09 | E | 854141 | KOREA, SOUTH | 6597 | 9.35 | 7.6 |
| 2026-09 | E | 381800 | ALL COUNTRIES | 150676 | 8.86 | 100.0 |
| 2026-09 | E | 848620 | ALL COUNTRIES | 958682 | 24.33 | 100.0 |
| 2026-09 | E | 851762 | ALL COUNTRIES | 2898564 | 41.96 | 100.0 |
| 2026-09 | E | 854141 | ALL COUNTRIES | 86685 | 24.81 | 100.0 |
| 2026-09 | E | 854149 | ALL COUNTRIES | 83560 | -53.14 | 100.0 |
| 2026-09 | I | 280461 | ALL COUNTRIES | 9945 | -49.26 | 100.0 |
| 2026-09 | I | 381800 | ALL COUNTRIES | 222573 | 59.67 | 100.0 |
| 2026-09 | I | 848610 | ALL COUNTRIES | 227980 | 834.54 | 100.0 |
| 2026-09 | I | 848620 | ALL COUNTRIES | 1511313 | 281.80 | 100.0 |
| 2026-09 | I | 848640 | ALL COUNTRIES | 155122 | 153.30 | 100.0 |
| 2026-09 | I | 848690 | ALL COUNTRIES | 486224 | 24.34 | 100.0 |
| 2026-09 | I | 851762 | ALL COUNTRIES | 13875081 | 88.29 | 100.0 |
| 2026-09 | I | 8517620090 | ALL COUNTRIES | 8012533 | 60.36 | 100.0 |
| 2026-09 | I | 851779 | ALL COUNTRIES | 239895 | 42.34 | 100.0 |
| 2026-09 | I | 854110 | ALL COUNTRIES | 54036 | 23.84 | 100.0 |
| 2026-09 | I | 854141 | ALL COUNTRIES | 51041 | 11.25 | 100.0 |
| 2026-09 | I | 854149 | ALL COUNTRIES | 76180 | -16.71 | 100.0 |
| 2026-09 | I | 854470 | ALL COUNTRIES | 705627 | 121.94 | 100.0 |
| 2026-09 | I | 900110 | ALL COUNTRIES | 68716 | 193.77 | 100.0 |
| 2026-09 | I | 901320 | ALL COUNTRIES | 92634 | 6.09 | 100.0 |
| 2026-09 | I | 901380 | ALL COUNTRIES | 181612 | 73.21 | 100.0 |

---
Validation status (constitution §21): raw government data, mechanically aggregated. Tier 1 screening input only; not a thesis, not advice.
