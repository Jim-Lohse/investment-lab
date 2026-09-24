# Does CFTC positioning lead the funds? Test results

Generated 2026-09-24 by `python -m signals.cftc_leadlag`. Main test acts at the close of the Monday after each report. 144 combinations tested; 12 pass the bar (|t| >= 2.5 and the same direction in 2006-2015 and 2016-2026).

| Fund | Who | Target | Signal | Weeks ahead | rho | t | Top fifth minus bottom fifth, % | rho 2006-15 | rho 2016-26 |
|---|---|---|---|---|---|---|---|---|---|
| GLD | Hedge funds | gld_tonnes | chg4 | 1 | 0.211 | 6.33 | 0.60 | 0.184 | 0.234 |
| GLD | Hedge funds | gld_tonnes | chg1 | 2 | 0.199 | 6.18 | 1.40 | 0.217 | 0.185 |
| GLD | Hedge funds | gld_tonnes | crowd | 1 | 0.216 | 6.13 | 0.64 | 0.228 | 0.207 |
| GLD | Hedge funds | gld_tonnes | chg1 | 3 | 0.202 | 6.06 | 1.87 | 0.192 | 0.212 |
| GLD | Hedge funds | gld_tonnes | chg1 | 4 | 0.193 | 5.75 | 2.05 | 0.160 | 0.221 |
| GLD | Hedge funds | gld_tonnes | chg4 | 2 | 0.224 | 5.67 | 1.07 | 0.145 | 0.294 |
| GLD | Hedge funds | gld_tonnes | crowd | 2 | 0.237 | 5.47 | 1.21 | 0.205 | 0.257 |
| GLD | Hedge funds | gld_tonnes | chg4 | 3 | 0.220 | 4.97 | 1.37 | 0.129 | 0.302 |
| GLD | Hedge funds | gld_tonnes | crowd | 3 | 0.244 | 4.85 | 1.67 | 0.202 | 0.264 |
| GLD | Hedge funds | gld_tonnes | chg1 | 1 | 0.154 | 4.83 | 0.67 | 0.190 | 0.128 |
| GLD | Hedge funds | gld_tonnes | chg4 | 4 | 0.204 | 4.33 | 1.62 | 0.099 | 0.300 |
| GLD | Hedge funds | gld_tonnes | crowd | 4 | 0.241 | 4.27 | 2.13 | 0.186 | 0.271 |

## GLD flows: what the CFTC signal adds beyond what is already known

Forward change in GLD's gold holdings regressed on the signal together with GLD's own holdings change and price return over the four weeks before entry (both published daily). Newey-West t-statistics.

| Signal | Weeks ahead | n | t, CFTC signal | t, past GLD flow | t, past GLD price |
|---|---|---|---|---|---|
| chg1 | 1 | 1056 | 1.82 | 4.57 | 3.12 |
| chg1 | 2 | 1055 | 2.69 | 4.53 | 3.21 |
| chg1 | 3 | 1054 | 2.78 | 4.77 | 3.10 |
| chg1 | 4 | 1053 | 2.09 | 4.46 | 3.04 |
| chg4 | 1 | 1053 | 1.22 | 4.16 | 3.33 |
| chg4 | 2 | 1052 | 0.49 | 4.18 | 4.04 |
| chg4 | 3 | 1051 | -0.06 | 4.50 | 4.06 |
| chg4 | 4 | 1050 | -0.22 | 4.24 | 3.87 |
| crowd | 1 | 953 | 1.37 | 3.82 | 4.17 |
| crowd | 2 | 952 | 1.27 | 3.73 | 4.29 |
| crowd | 3 | 951 | 0.93 | 3.92 | 4.01 |
| crowd | 4 | 950 | 0.81 | 3.70 | 3.31 |

Full table: `data/derived/cftc_leadlag.csv`. Method and caveats: the docstring of `signals/cftc_leadlag.py`.
