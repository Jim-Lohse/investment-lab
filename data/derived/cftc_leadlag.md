# Does CFTC positioning lead the funds? Test results

Generated 2026-09-24 by `python -m signals.cftc_leadlag`. Main test acts at the close of the Monday after each report. 128 combinations tested; 0 pass the bar (|t| >= 2.5 and the same direction in 2006-2015 and 2016-2026).

No combination passes the bar.

Full table: `data/derived/cftc_leadlag.csv`. Method and caveats: the docstring of `signals/cftc_leadlag.py`.
