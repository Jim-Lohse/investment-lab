# Demand-signal snapshot: Taiwan monthly revenue + Korea exports + Japan + U.S. trade

_Generated 2026-09-15 by `signals/compute_signals.py`._
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
| all_listed | 1964 | 49.55 | 15.21 | 72.4 |

_2026-07 ai_compute agg YoY: 42.67%_

## Korea trade (KCS)

| Period | Window | Item | USD k | YoY % |
|---|---|---|---:|---:|
| 2026-09 | D10 | exp:중국 | 7953248 | 102.95 |
| 2026-09 | D10 | exp:철강제품 | 1362183 | 10.27 |
| 2026-09 | D10 | exp:컴퓨터주변기기 | 634522 | 93.10 |
| 2026-09 | D10 | exp:홍콩 | 1788360 | 165.23 |
| 2026-09 | D10 | imp:TOTAL | 24606467 | 20.72 |
| 2026-09 | D10 | imp:가스 | 807140 | -9.70 |
| 2026-09 | D10 | imp:기계류 | 1003815 | -2.72 |
| 2026-09 | D10 | imp:대만 | 1669001 | 59.86 |
| 2026-09 | D10 | imp:러시아 연방 | 329288 | 43.71 |
| 2026-09 | D10 | imp:말레이시아 | 589612 | 9.07 |
| 2026-09 | D10 | imp:무선통신기기 | 380075 | 115.40 |
| 2026-09 | D10 | imp:미국 | 2408745 | 17.31 |
| 2026-09 | D10 | imp:반도체 | 4946515 | 91.48 |
| 2026-09 | D10 | imp:반도체제조용장비 | 1328000 | 44.77 |
| 2026-09 | D10 | imp:베트남 | 1274374 | 23.34 |
| 2026-09 | D10 | imp:사우디아라비아 | 837664 | -11.67 |
| 2026-09 | D10 | imp:석유제품 | 545880 | -38.37 |
| 2026-09 | D10 | imp:석탄 | 458951 | 15.08 |
| 2026-09 | D10 | imp:승용차 | 705249 | 70.90 |
| 2026-09 | D10 | imp:원유 | 2472510 | 3.47 |
| 2026-09 | D10 | imp:유럽연합 | 2371474 | 6.45 |
| 2026-09 | D10 | imp:일본 | 2220381 | 39.81 |
| 2026-09 | D10 | imp:정밀기기 | 611598 | 3.36 |
| 2026-09 | D10 | imp:중국 | 6996768 | 49.98 |
| 2026-09 | D10 | imp:호주 | 950553 | -0.67 |

## Japan trade (MOF / Customs) — supply side

_YoY in yen is what MOF publishes. YoY in USD restates the same series at the reference rate for that window; FX pt is the difference, the share of the published growth that is the currency rather than the trade._

| Period | Window | Source | Item | JPY m | YoY % (yen) | YoY % (USD) | FX pt | YoY % (MOF) |
|---|---|---|---|---:|---:|---:|---:|---:|
| 2026-07 | MONTH | press_release | BAL:Grand Total | -638344 | 438.95 | 387.23 | 51.72 | 308.50 |
| 2026-07 | MONTH | press_release | E:(IC) | 659368 | 51.95 | 37.37 | 14.58 | 52 |
| 2026-07 | MONTH | press_release | E:ELECTRICAL MEASURING | 228432 | 26.81 | 14.64 | 12.17 | 26.80 |
| 2026-07 | MONTH | press_release | E:Grand Total | 11509374 | 22.97 | 11.17 | 11.80 | 23.20 |
| 2026-07 | MONTH | press_release | E:SCIENTIFIC, OPTICAL INST | 271075 | 16.47 | 5.29 | 11.18 | 16.50 |
| 2026-07 | MONTH | press_release | E:SEMICON MACHINERY ETC | 493950 | 40.75 | 27.24 | 13.51 | 40.70 |
| 2026-07 | MONTH | press_release | E:SEMICONDUCTORS ETC | 862099 | 49.07 | 34.76 | 14.31 | 49.10 |
| 2026-07 | MONTH | press_release | E:TELEPHONY, TELEGRAPHY | 34047 | 20.59 | 9.02 | 11.57 | 20.60 |
| 2026-07 | MONTH | press_release | I:(IC) | 493295 | 92.65 | 74.16 | 18.49 | 92.60 |
| 2026-07 | MONTH | press_release | I:ELECTRICAL MEASURING | 112202 | 31.62 | 18.99 | 12.63 | 31.50 |
| 2026-07 | MONTH | press_release | I:Grand Total | 12147718 | 28.17 | 15.87 | 12.30 | 27.90 |
| 2026-07 | MONTH | press_release | I:SCIENTIFIC, OPTICAL INST | 244216 | 10.48 | -0.12 | 10.60 | 10.50 |
| 2026-07 | MONTH | press_release | I:SEMICONDUCTORS ETC | 547093 | 79.71 | 62.46 | 17.25 | 79.70 |
| 2026-07 | MONTH | press_release | I:TELEPHONY, TELEGRAPHY | 461870 | 48.19 | 33.97 | 14.22 | 48.20 |
| 2026-08 | D10 | press_release | BAL:Grand Total | 217306 | -51.62 | -54.60 | 2.98 | -50 |
| 2026-08 | D10 | press_release | E:Grand Total | 3678584 | 15.50 | 8.39 | 7.11 | 15.50 |
| 2026-08 | D10 | press_release | I:Grand Total | 3461278 | 26.52 | 18.73 | 7.79 | 25.80 |
| 2026-08 | D20 | press_release | BAL:Grand Total | -1119533 | 111.83 | 97.36 | 14.47 | 100.70 |
| 2026-08 | D20 | press_release | E:Grand Total | 6050366 | 17.93 | 9.87 | 8.06 | 18 |
| 2026-08 | D20 | press_release | I:Grand Total | 7169899 | 26.70 | 18.04 | 8.66 | 26.10 |
| 2026-07 | MONTH | timeseries:world_exports_by_commodity | E:半導体等製造装置 | 493950 | 40.75 | 27.24 | 13.51 |  |
| 2026-07 | MONTH | timeseries:world_exports_by_commodity | E:半導体等電子部品 | 862099 | 49.07 | 34.76 | 14.31 |  |
| 2026-07 | MONTH | timeseries:world_exports_by_commodity | E:科学光学機器 | 271075 | 16.48 | 5.30 | 11.18 |  |
| 2026-07 | MONTH | timeseries:world_exports_by_commodity | E:総額 | 11509374 | 23.16 | 11.34 | 11.82 |  |
| 2026-07 | MONTH | timeseries:world_imports_by_commodity | I:半導体等電子部品 | 547093 | 79.69 | 62.45 | 17.24 |  |
| 2026-07 | MONTH | timeseries:world_imports_by_commodity | I:科学光学機器 | 244216 | 10.45 | -0.15 | 10.60 |  |
| 2026-07 | MONTH | timeseries:world_imports_by_commodity | I:総額 | 12147718 | 27.86 | 15.59 | 12.27 |  |
| 2026-07 | MONTH | estat_hs:DETAILED | E:HS280461 | 3461 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:DETAILED | E:HS3818 | 63046 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:DETAILED | E:HS8486 | 493950 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:DETAILED | E:HS8517 | 26837 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:DETAILED | E:HS8541 | 143147 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:DETAILED | E:HS8542 | 715777 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:DETAILED | E:HS854470 | 5661 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:DETAILED | E:HS9001 | 41230 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:DETAILED | E:HS9013 | 10990 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:PROV9 | I:HS280461 | 6838 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:PROV9 | I:HS3818 | 17139 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:PROV9 | I:HS8486 | 103303 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:PROV9 | I:HS8517 | 437747 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:PROV9 | I:HS8541 | 47162 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:PROV9 | I:HS8542 | 497299 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:PROV9 | I:HS854470 | 3449 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:PROV9 | I:HS9001 | 35553 |  |  |  |  |
| 2026-07 | MONTH | estat_hs:PROV9 | I:HS9013 | 10915 |  |  |  |  |

_Reference rate, newest window stored: 158.56 yen per USD (2026-08)._

## U.S. trade by HTS code (Census) — demand side

| Period | I/E | Code | Country | USD k | YoY % | Share of code % |
|---|---|---|---|---:|---:|---:|
| 2026-07 | I | 381800 | TAIWAN | 54260 | 163.37 | 30.4 |
| 2026-07 | I | 381800 | JAPAN | 49367 | -9.32 | 27.7 |
| 2026-07 | I | 381800 | KOREA, SOUTH | 19315 | 6.11 | 10.8 |
| 2026-07 | I | 381800 | GERMANY | 9455 | -12.92 | 5.3 |
| 2026-07 | I | 381800 | CHINA | 8529 | 54.86 | 4.8 |
| 2026-07 | I | 381800 | SINGAPORE | 8202 | 146.20 | 4.6 |
| 2026-07 | I | 848620 | NETHERLANDS | 163183 | 7.02 | 24.5 |
| 2026-07 | I | 848620 | JAPAN | 121787 | -2.73 | 18.3 |
| 2026-07 | I | 848620 | KOREA, SOUTH | 104676 | 228.63 | 15.7 |
| 2026-07 | I | 848620 | SINGAPORE | 92525 | 3.73 | 13.9 |
| 2026-07 | I | 848620 | MALAYSIA | 64819 | 19.06 | 9.7 |
| 2026-07 | I | 848620 | CHINA | 31502 | 220.44 | 4.7 |
| 2026-07 | I | 8517620090 | THAILAND | 2855291 | 106.12 | 40.0 |
| 2026-07 | I | 8517620090 | VIETNAM | 1485863 | 85.44 | 20.8 |
| 2026-07 | I | 8517620090 | TAIWAN | 723469 | 83.05 | 10.1 |
| 2026-07 | I | 8517620090 | MALAYSIA | 574341 | 13.93 | 8.0 |
| 2026-07 | I | 8517620090 | MEXICO | 499092 | -22.46 | 7.0 |
| 2026-07 | I | 8517620090 | CHINA | 328800 | -13.93 | 4.6 |
| 2026-07 | I | 854141 | CHINA | 11820 | -7.92 | 20.2 |
| 2026-07 | I | 854141 | JAPAN | 11104 | -15.75 | 19.0 |
| 2026-07 | I | 854141 | TAIWAN | 10751 | 49.95 | 18.4 |
| 2026-07 | I | 854141 | MALAYSIA | 7520 | -26.97 | 12.8 |
| 2026-07 | I | 854141 | GERMANY | 6214 | 51.01 | 10.6 |
| 2026-07 | I | 854141 | THAILAND | 3506 | 33.72 | 6.0 |
| 2026-07 | E | 381800 | OMAN | 40046 |  | 22.2 |
| 2026-07 | E | 381800 | MALAYSIA | 25394 | -29.61 | 14.1 |
| 2026-07 | E | 381800 | TAIWAN | 20626 | 38.06 | 11.4 |
| 2026-07 | E | 381800 | JAPAN | 17866 | -14.49 | 9.9 |
| 2026-07 | E | 381800 | SINGAPORE | 13535 | 30.87 | 7.5 |
| 2026-07 | E | 381800 | FRANCE | 11705 | 1594.88 | 6.5 |
| 2026-07 | E | 848620 | TAIWAN | 391410 | -23.15 | 33.6 |
| 2026-07 | E | 848620 | KOREA, SOUTH | 312478 | 20.77 | 26.8 |
| 2026-07 | E | 848620 | SINGAPORE | 146573 | 309.55 | 12.6 |
| 2026-07 | E | 848620 | IRELAND | 100029 | 1693.84 | 8.6 |
| 2026-07 | E | 848620 | JAPAN | 65555 | -22.22 | 5.6 |
| 2026-07 | E | 848620 | CHINA | 41164 | -83.95 | 3.5 |
| 2026-07 | E | 854141 | THAILAND | 13132 | 323.59 | 18.1 |
| 2026-07 | E | 854141 | MEXICO | 11307 | -22.12 | 15.6 |
| 2026-07 | E | 854141 | GERMANY | 10231 | -44.10 | 14.1 |
| 2026-07 | E | 854141 | KOREA, SOUTH | 6069 | -9.98 | 8.4 |
| 2026-07 | E | 854141 | CHINA | 5439 | -34.70 | 7.5 |
| 2026-07 | E | 854141 | HONG KONG | 5217 | -30.62 | 7.2 |
| 2026-07 | E | 381800 | ALL COUNTRIES | 180582 | 18.29 | 100.0 |
| 2026-07 | E | 848620 | ALL COUNTRIES | 1163939 | -8.05 | 100.0 |
| 2026-07 | E | 851762 | ALL COUNTRIES | 2792290 | 29.75 | 100.0 |
| 2026-07 | E | 854141 | ALL COUNTRIES | 72552 | -9.45 | 100.0 |
| 2026-07 | E | 854149 | ALL COUNTRIES | 83632 | 2.24 | 100.0 |
| 2026-07 | I | 280461 | ALL COUNTRIES | 6458 | -58.55 | 100.0 |
| 2026-07 | I | 381800 | ALL COUNTRIES | 178327 | 29.84 | 100.0 |
| 2026-07 | I | 848610 | ALL COUNTRIES | 44662 | 12.14 | 100.0 |
| 2026-07 | I | 848620 | ALL COUNTRIES | 665569 | 15.96 | 100.0 |
| 2026-07 | I | 848640 | ALL COUNTRIES | 240575 | 185.69 | 100.0 |
| 2026-07 | I | 848690 | ALL COUNTRIES | 396914 | 25.53 | 100.0 |
| 2026-07 | I | 851762 | ALL COUNTRIES | 12406596 | 64.57 | 100.0 |
| 2026-07 | I | 8517620090 | ALL COUNTRIES | 7143769 | 56.09 | 100.0 |
| 2026-07 | I | 851779 | ALL COUNTRIES | 221678 | 19.69 | 100.0 |
| 2026-07 | I | 854110 | ALL COUNTRIES | 56652 | 38.13 | 100.0 |
| 2026-07 | I | 854141 | ALL COUNTRIES | 58543 | 3.44 | 100.0 |
| 2026-07 | I | 854149 | ALL COUNTRIES | 81145 | -6.49 | 100.0 |
| 2026-07 | I | 854470 | ALL COUNTRIES | 543288 | 38.68 | 100.0 |
| 2026-07 | I | 900110 | ALL COUNTRIES | 70909 | 225.60 | 100.0 |
| 2026-07 | I | 901320 | ALL COUNTRIES | 85398 | 2.29 | 100.0 |
| 2026-07 | I | 901380 | ALL COUNTRIES | 148984 | -2.85 | 100.0 |

---
Validation status (constitution §21): raw government data, mechanically aggregated. Tier 1 screening input only; not a thesis, not advice.
