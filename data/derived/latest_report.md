# Demand-signal snapshot: Taiwan monthly revenue + Korea exports + Japan trade

_Generated 2026-09-02 by `signals/compute_signals.py`._
_Derived data; the underlying records in `data/` are the source of truth._

## Taiwan monthly revenue — 2026-07

| Group | n | Agg YoY % | Median YoY % | Breadth % |
|---|---:|---:|---:|---:|
| ai_compute | 5 | 42.67 | 97.59 | 100.0 |
| ai_server_odm | 5 | 65.83 | 60.76 | 100.0 |
| power_cooling | 5 | 49.06 | 47.75 | 80.0 |
| robotics_motion | 3 | 42.35 | 33.94 | 100.0 |
| network_interconnect | 3 | 66.04 | 59.59 | 100.0 |
| photonics_epi | 2 | 95.57 | 110.83 | 100.0 |
| photonics_cpo | 8 | 37.26 | 31.09 | 100.0 |
| all_listed | 1967 | 41.79 | 16.14 | 73.8 |

## Korea trade (KCS)

| Period | Window | Item | USD k | YoY % |
|---|---|---|---:|---:|
| 2026-08 | FULL | exp:중국 | 24098821 |  |
| 2026-08 | FULL | exp:철강제품 | 4032546 |  |
| 2026-08 | FULL | exp:컴퓨터주변기기 | 6410085 |  |
| 2026-08 | FULL | exp:홍콩 | 8902410 |  |
| 2026-08 | FULL | imp:TOTAL | 63507072 |  |
| 2026-08 | FULL | imp:가스 | 2777777 |  |
| 2026-08 | FULL | imp:기계류 | 2632081 |  |
| 2026-08 | FULL | imp:대만 | 4719181 |  |
| 2026-08 | FULL | imp:러시아 연방 | 840432 |  |
| 2026-08 | FULL | imp:말레이시아 | 1480404 |  |
| 2026-08 | FULL | imp:무선통신기기 | 1083731 |  |
| 2026-08 | FULL | imp:미국 | 7605579 |  |
| 2026-08 | FULL | imp:반도체 | 11367459 |  |
| 2026-08 | FULL | imp:반도체제조용장비 | 3015343 |  |
| 2026-08 | FULL | imp:베트남 | 3687492 |  |
| 2026-08 | FULL | imp:사우디아라비아 | 1965505 |  |
| 2026-08 | FULL | imp:석유제품 | 1370211 |  |
| 2026-08 | FULL | imp:석탄 | 1616769 |  |
| 2026-08 | FULL | imp:승용차 | 1262517 |  |
| 2026-08 | FULL | imp:원유 | 8284800 |  |
| 2026-08 | FULL | imp:유럽연합 | 5963461 |  |
| 2026-08 | FULL | imp:일본 | 4757672 |  |
| 2026-08 | FULL | imp:정밀기기 | 1598369 |  |
| 2026-08 | FULL | imp:중국 | 15325220 |  |
| 2026-08 | FULL | imp:호주 | 2930015 |  |

## Japan trade (MOF / Customs) — supply side

| Period | Window | Source | Item | JPY m | YoY % (store) | YoY % (published) |
|---|---|---|---|---:|---:|---:|
| 2026-07 | D20 | press_release | BAL:Grand Total | 37102 |  | -71.90 |
| 2026-07 | D20 | press_release | E:Grand Total | 7231361 |  | 20.40 |
| 2026-07 | D20 | press_release | I:Grand Total | 7194259 |  | 22.50 |
| 2026-07 | MONTH | press_release | BAL:Grand Total | -638344 |  | 308.50 |
| 2026-07 | MONTH | press_release | E:(IC) | 659368 |  | 52 |
| 2026-07 | MONTH | press_release | E:ELECTRICAL MEASURING | 228432 |  | 26.80 |
| 2026-07 | MONTH | press_release | E:Grand Total | 11509374 |  | 23.20 |
| 2026-07 | MONTH | press_release | E:SCIENTIFIC, OPTICAL INST | 271075 |  | 16.50 |
| 2026-07 | MONTH | press_release | E:SEMICON MACHINERY ETC | 493950 |  | 40.70 |
| 2026-07 | MONTH | press_release | E:SEMICONDUCTORS ETC | 862099 |  | 49.10 |
| 2026-07 | MONTH | press_release | E:TELEPHONY, TELEGRAPHY | 34047 |  | 20.60 |
| 2026-07 | MONTH | press_release | I:(IC) | 493295 |  | 92.60 |
| 2026-07 | MONTH | press_release | I:ELECTRICAL MEASURING | 112202 |  | 31.50 |
| 2026-07 | MONTH | press_release | I:Grand Total | 12147718 |  | 27.90 |
| 2026-07 | MONTH | press_release | I:SCIENTIFIC, OPTICAL INST | 244216 |  | 10.50 |
| 2026-07 | MONTH | press_release | I:SEMICONDUCTORS ETC | 547093 |  | 79.70 |
| 2026-07 | MONTH | press_release | I:TELEPHONY, TELEGRAPHY | 461870 |  | 48.20 |
| 2026-08 | D10 | press_release | BAL:Grand Total | 217306 |  | -50 |
| 2026-08 | D10 | press_release | E:Grand Total | 3678584 |  | 15.50 |
| 2026-08 | D10 | press_release | I:Grand Total | 3461278 |  | 25.80 |
| 2026-07 | MONTH | timeseries:world_exports_by_commodity | E:半導体等製造装置 | 493950 | 40.75 |  |
| 2026-07 | MONTH | timeseries:world_exports_by_commodity | E:半導体等電子部品 | 862099 | 49.07 |  |
| 2026-07 | MONTH | timeseries:world_exports_by_commodity | E:科学光学機器 | 271075 | 16.48 |  |
| 2026-07 | MONTH | timeseries:world_exports_by_commodity | E:総額 | 11509374 | 23.16 |  |
| 2026-07 | MONTH | timeseries:world_imports_by_commodity | I:半導体等電子部品 | 547093 | 79.69 |  |
| 2026-07 | MONTH | timeseries:world_imports_by_commodity | I:科学光学機器 | 244216 | 10.45 |  |
| 2026-07 | MONTH | timeseries:world_imports_by_commodity | I:総額 | 12147718 | 27.86 |  |

---
Validation status (constitution §21): raw government data, mechanically aggregated. Tier 1 screening input only; not a thesis, not advice.
