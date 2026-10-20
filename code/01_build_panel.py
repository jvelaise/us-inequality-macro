"""Build the annual US inequality/macro panel from raw FRED downloads.

Input : data/raw/{A191RL1A225NBEA,CPIAUCSL,FYFSGDA188S,UNRATE,GINIALLRF}.csv
Output: data/us_macro_annual.csv

Conventions, stated here because they are choices rather than defaults:

* Monthly series are aggregated to calendar-year means using COMPLETE years
  only. A partial final year is dropped rather than averaged over fewer than
  12 months.
* Inflation is produced in two forms -- annual-average and December-over-
  December -- because they differ materially in individual years (4.68 vs
  7.17 percent in 2021) and the right choice depends on how inflation is
  dated against annual income. Downstream code picks one explicitly.
* The panel is trimmed at 2025, the last year for which every annual source
  reports.
"""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "us_macro_annual.csv"
LAST_YEAR = 2025

SERIES = {
    "A191RL1A225NBEA": "gdp_growth",             # real GDP growth, % p.a., annual
    "FYFSGDA188S": "fiscal_balance_pct_gdp",     # federal surplus/deficit, % GDP, annual
    "CPIAUCSL": "cpi",                           # CPI index, monthly
    "UNRATE": "unemployment_rate",               # unemployment rate, %, monthly
    "GINIALLRF": "gini_families",                # Census Gini, annual
}


def load(series_id):
    df = pd.read_csv(RAW / f"{series_id}.csv")
    df["date"] = pd.to_datetime(df["observation_date"])
    df["year"] = df["date"].dt.year
    return df.rename(columns={series_id: "value"})[["date", "year", "value"]]


def annual_mean_complete_years(df):
    """Calendar-year mean over complete 12-month years only."""
    counts = df.groupby("year")["value"].size()
    complete = counts[counts == 12].index
    return df[df["year"].isin(complete)].groupby("year")["value"].mean()


def main():
    raw = {sid: load(sid) for sid in SERIES}

    gini = raw["GINIALLRF"].set_index("year")["value"].rename("gini_families")
    gdp = raw["A191RL1A225NBEA"].set_index("year")["value"].rename("gdp_growth")
    fiscal = raw["FYFSGDA188S"].set_index("year")["value"].rename("fiscal_balance_pct_gdp")

    cpi = raw["CPIAUCSL"]
    cpi_avg = annual_mean_complete_years(cpi)
    cpi_dec = cpi[cpi["date"].dt.month == 12].set_index("year")["value"]
    inflation_avg = (cpi_avg.pct_change() * 100).rename("inflation_cpi_avg")
    inflation_dec = (cpi_dec.pct_change() * 100).rename("inflation_cpi_dec")

    unemployment = annual_mean_complete_years(raw["UNRATE"]).rename("unemployment_rate")

    panel = pd.concat([gini, gdp, inflation_avg, inflation_dec, fiscal, unemployment], axis=1)
    panel = panel.sort_index().loc[:LAST_YEAR]
    panel.index.name = "year"

    complete = panel.dropna()
    assert len(complete) > 70, f"unexpectedly short complete-case sample: {len(complete)}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    panel.round(4).to_csv(OUT)
    print(f"wrote {OUT.relative_to(ROOT)}: {panel.index.min()}-{panel.index.max()}, "
          f"{len(panel)} rows; complete cases {complete.index.min()}-{complete.index.max()} "
          f"(n={len(complete)})")


if __name__ == "__main__":
    main()
