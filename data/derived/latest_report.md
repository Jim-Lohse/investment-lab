# Demand-signal snapshot: Taiwan monthly revenue + Korea exports + Japan + U.S. trade

_Generated 2026-10-06 by `signals/compute_signals.py`._
_Derived data; the underlying records in `data/` are the source of truth._

## Taiwan monthly revenue — 2026-08

| Group | n | Agg YoY % | Median YoY % | Breadth % |
|---|---:|---:|---:|---:|
| ai_compute | 5 | 54.13 | 111.02 | 100.0 |
| ai_server_odm | 5 | 86.68 | 51.98 | 100.0 |
| power_cooling | 5 | 38.81 | 34.95 | 100.0 |
| robotics_motion | 3 | 42.03 | 42.30 | 100.0 |
| network_interconnect | 3 | 56.53 | 53.99 | 100.0 |
| photonics_epi | 2 | 115.32 | 126.03 | 100.0 |
| photonics_cpo | 8 | 62.59 | 43.63 | 100.0 |
| all_listed | 1970 | 46.36 | 15.17 | 72.2 |

_2026-07 ai_compute agg YoY: 42.67%_

## Korea trade (KCS)

| Period | Window | Item | USD k | YoY % |
|---|---|---|---:|---:|
| 2026-09 | FULL | exp:중국 | 26013702 | 122.73 |
| 2026-09 | FULL | exp:철강제품 | 4277639 | 6.65 |
| 2026-09 | FULL | exp:컴퓨터주변기기 | 7145115 | 392.31 |
| 2026-09 | FULL | exp:홍콩 | 10573575 | 202.36 |
| 2026-09 | FULL | imp:TOTAL | 71092194 | 26.01 |
| 2026-09 | FULL | imp:가스 | 3521462 | 43.19 |
| 2026-09 | FULL | imp:기계류 | 2760728 | -0.29 |
| 2026-09 | FULL | imp:대만 | 5038428 | 78.67 |
| 2026-09 | FULL | imp:러시아 연방 | 891942 | 24.50 |
| 2026-09 | FULL | imp:말레이시아 | 1741466 | 29.46 |
| 2026-09 | FULL | imp:무선통신기기 | 1784021 | 29.75 |
| 2026-09 | FULL | imp:미국 | 7061118 | 18.95 |
| 2026-09 | FULL | imp:반도체 | 12737591 | 92.79 |
| 2026-09 | FULL | imp:반도체제조용장비 | 4021809 | 49.23 |
| 2026-09 | FULL | imp:베트남 | 3621231 | 26.36 |
| 2026-09 | FULL | imp:사우디아라비아 | 1892080 | -11.63 |
| 2026-09 | FULL | imp:석유제품 | 1609944 | -14.17 |
| 2026-09 | FULL | imp:석탄 | 1482767 | 24.17 |
| 2026-09 | FULL | imp:승용차 | 1611533 | 31.80 |
| 2026-09 | FULL | imp:원유 | 7961010 | 38.44 |
| 2026-09 | FULL | imp:유럽연합 | 7208917 | 5.58 |
| 2026-09 | FULL | imp:일본 | 5228035 | 22.54 |
| 2026-09 | FULL | imp:정밀기기 | 1695892 | 1.73 |
| 2026-09 | FULL | imp:중국 | 19293306 | 42.82 |
| 2026-09 | FULL | imp:호주 | 3151917 | 13.81 |

## Japan trade (MOF / Customs) — supply side

_YoY in yen is what MOF publishes. YoY in USD restates the same series at the reference rate for that window; FX pt is the difference, the share of the published growth that is the currency rather than the trade._

| Period | Window | Source | Item | JPY m | YoY % (yen) | YoY % (USD) | FX pt | YoY % (MOF) |
|---|---|---|---|---:|---:|---:|---:|---:|
| 2026-08 | D20 | press_release | BAL:Grand Total | -1119533 | 111.83 | 97.36 | 14.47 | 100.70 |
| 2026-08 | D20 | press_release | E:Grand Total | 6050366 | 17.93 | 9.87 | 8.06 | 18 |
| 2026-08 | D20 | press_release | I:Grand Total | 7169899 | 26.70 | 18.04 | 8.66 | 26.10 |
| 2026-08 | MONTH | press_release | BAL:Grand Total | -1111913 | 357.99 | 325.96 | 32.03 | 278.10 |
| 2026-08 | MONTH | press_release | E:(IC) | 697209 | 56.89 | 45.92 | 10.97 | 56.90 |
| 2026-08 | MONTH | press_release | E:ELECTRICAL MEASURING | 199780 | 20.38 | 11.96 | 8.42 | 20.40 |
| 2026-08 | MONTH | press_release | E:Grand Total | 10043270 | 19.20 | 10.86 | 8.34 | 19.30 |
| 2026-08 | MONTH | press_release | E:SCIENTIFIC, OPTICAL INST | 250890 | 19.51 | 11.15 | 8.36 | 19.50 |
| 2026-08 | MONTH | press_release | E:SEMICON MACHINERY ETC | 489701 | 40.12 | 30.33 | 9.79 | 40.10 |
| 2026-08 | MONTH | press_release | E:SEMICONDUCTORS ETC | 894119 | 52.25 | 41.61 | 10.64 | 52.30 |
| 2026-08 | MONTH | press_release | E:TELEPHONY, TELEGRAPHY | 27616 | 14.53 | 6.52 | 8.01 | 14.50 |
| 2026-08 | MONTH | press_release | I:(IC) | 546544 | 93.25 | 79.74 | 13.51 | 93.30 |
| 2026-08 | MONTH | press_release | I:ELECTRICAL MEASURING | 98992 | 10.20 | 2.50 | 7.70 | 10.10 |
| 2026-08 | MONTH | press_release | I:Grand Total | 11155183 | 28.69 | 19.69 | 9.00 | 28 |
| 2026-08 | MONTH | press_release | I:SCIENTIFIC, OPTICAL INST | 226285 | 15.67 | 7.58 | 8.09 | 15.60 |
| 2026-08 | MONTH | press_release | I:SEMICONDUCTORS ETC | 599831 | 82.14 | 69.41 | 12.73 | 82.10 |
| 2026-08 | MONTH | press_release | I:TELEPHONY, TELEGRAPHY | 325576 | 23.76 | 15.11 | 8.65 | 23.70 |
| 2026-09 | D10 | press_release | BAL:Grand Total | -421205 | -18.80 | -23.07 | 4.27 | -21.50 |
| 2026-09 | D10 | press_release | E:Grand Total | 3821914 | 23.33 | 16.84 | 6.49 | 23.30 |
| 2026-09 | D10 | press_release | I:Grand Total | 4243119 | 17.29 | 11.12 | 6.17 | 16.70 |
| 2026-08 | MONTH | timeseries:world_exports_by_commodity | E:半導体等製造装置 | 489701 | 40.12 | 30.32 | 9.80 |  |
| 2026-08 | MONTH | timeseries:world_exports_by_commodity | E:半導体等電子部品 | 894119 | 52.25 | 41.61 | 10.64 |  |
| 2026-08 | MONTH | timeseries:world_exports_by_commodity | E:科学光学機器 | 250890 | 19.51 | 11.15 | 8.36 |  |
| 2026-08 | MONTH | timeseries:world_exports_by_commodity | E:総額 | 10043270 | 19.28 | 10.94 | 8.34 |  |
| 2026-08 | MONTH | timeseries:world_imports_by_commodity | I:半導体等電子部品 | 599831 | 82.14 | 69.41 | 12.73 |  |
| 2026-08 | MONTH | timeseries:world_imports_by_commodity | I:科学光学機器 | 226285 | 15.63 | 7.55 | 8.08 |  |
| 2026-08 | MONTH | timeseries:world_imports_by_commodity | I:総額 | 11155183 | 28.01 | 19.06 | 8.95 |  |
| 2026-08 | MONTH | estat_hs:DETAILED | E:HS280461 | 3385 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:DETAILED | E:HS3818 | 70113 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:DETAILED | E:HS8486 | 489701 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:DETAILED | E:HS8517 | 21732 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:DETAILED | E:HS8541 | 139884 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:DETAILED | E:HS8542 | 751091 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:DETAILED | E:HS854470 | 5520 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:DETAILED | E:HS9001 | 39050 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:DETAILED | E:HS9013 | 10546 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:PROV9 | I:HS280461 | 8333 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:PROV9 | I:HS3818 | 17817 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:PROV9 | I:HS8486 | 76939 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:PROV9 | I:HS8517 | 305387 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:PROV9 | I:HS8541 | 45586 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:PROV9 | I:HS8542 | 551434 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:PROV9 | I:HS854470 | 6045 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:PROV9 | I:HS9001 | 33202 |  |  |  |  |
| 2026-08 | MONTH | estat_hs:PROV9 | I:HS9013 | 11819 |  |  |  |  |

_Reference rate, newest window stored: 156.06 yen per USD (2026-09)._

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
