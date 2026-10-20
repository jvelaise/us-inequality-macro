"""Local-projection estimates of the Gini response to macro variables, plus figure.

Input : data/us_macro_annual.csv
Output: outputs/lp_gini_response.csv, outputs/gini_local_projections.png

Specification (Jorda local projections). For each macro variable x and each
horizon h = 0..H:

    100*(G_{t+h} - G_{t-1}) = a_h + b_h * x_t
                              + sum_{j=1..P} controls_{t-j} + e_{t+h}

where G is the Gini (0-1 scale, multiplied by 100 so coefficients read as
index points) and the control block is P lags of the Gini change and of all
four macro variables. Standard errors are Newey-West with h+1 lags.

b_h is a PREDICTIVE response, not an identified causal effect: x_t is the
realised macro variable, not an identified shock.
"""
import pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "us_macro_annual.csv"
OUTDIR = ROOT / "outputs"

INFLATION = "inflation_cpi_avg"   # alternative: "inflation_cpi_dec"
SHOCKS = ["gdp_growth", INFLATION, "fiscal_balance_pct_gdp"]
CONTROLS = ["dgini", "gdp_growth", INFLATION, "fiscal_balance_pct_gdp", "unemployment_rate"]
P, H = 2, 8
Z90 = 1.645

TITLES = {
    "gdp_growth": "Faster growth narrows inequality for about four years",
    "inflation_cpi_avg": "Inflation narrows it early, widens it after about four years",
    "inflation_cpi_dec": "Inflation narrows it early, widens it after about four years",
    "fiscal_balance_pct_gdp": "Fiscal balance: no reliable link at most horizons",
}
XLABELS = {
    "gdp_growth": "Years after a 1 pp rise in real GDP growth",
    "inflation_cpi_avg": "Years after a 1 pp rise in CPI inflation",
    "inflation_cpi_dec": "Years after a 1 pp rise in CPI inflation",
    "fiscal_balance_pct_gdp": "Years after a 1 pp rise in the fiscal balance",
}
GREY, FILL, LINE = "#808080", "#4C72B0", "#1F4E79"


def estimate(d):
    rows = []
    for s in SHOCKS:
        for h in range(H + 1):
            X = pd.DataFrame({f"{s}_t": d[s]}, index=d.index)
            for c in CONTROLS:
                for j in range(1, P + 1):
                    X[f"{c}_l{j}"] = d[c].shift(j)
            y = (d["gini100"].shift(-h) - d["gini100"].shift(1)).rename("y")
            dat = pd.concat([y, X], axis=1).dropna()
            res = sm.OLS(dat["y"], sm.add_constant(dat.drop(columns="y"))).fit(
                cov_type="HAC", cov_kwds={"maxlags": h + 1})
            b, se = res.params[f"{s}_t"], res.bse[f"{s}_t"]
            rows.append(dict(shock=s, horizon=h, beta=b, se=se,
                             lo90=b - Z90 * se, hi90=b + Z90 * se,
                             t=b / se, n=int(res.nobs)))
    return pd.DataFrame(rows)


def plot(lp, path):
    plt.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
                         "xtick.labelsize": 6, "ytick.labelsize": 6,
                         "xtick.direction": "out", "ytick.direction": "out",
                         "figure.dpi": 300, "savefig.dpi": 300})
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4), sharey=True)
    for ax, s in zip(axes, SHOCKS):
        sub = lp[lp.shock == s].sort_values("horizon")
        ax.axhline(0, color=GREY, lw=0.8, zorder=1)
        ax.fill_between(sub.horizon, sub.lo90, sub.hi90, color=FILL, alpha=0.18, lw=0, zorder=2)
        ax.plot(sub.horizon, sub.beta, color=LINE, lw=1.8, marker="o", ms=3.5, zorder=3)
        ax.set_title(TITLES[s], loc="left")
        ax.set_xlabel(XLABELS[s])
        ax.margins(0.04)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].set_ylabel("Cumulative change in Gini\n(index points)")
    axes[0].text(0.03, 0.06, "shaded: 90% HAC band", transform=axes[0].transAxes,
                 fontsize=6, color=GREY)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    return fig


def main():
    d = pd.read_csv(PANEL, index_col="year")
    d["gini100"] = d["gini_families"] * 100
    d["dgini"] = d["gini100"].diff()

    lp = estimate(d)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    lp.round(4).to_csv(OUTDIR / "lp_gini_response.csv", index=False)
    plot(lp, OUTDIR / "gini_local_projections.png")

    for s in SHOCKS:
        sub = lp[lp.shock == s]
        i = sub.beta.abs().idxmax()
        sig = [int(r.horizon) for r in sub.itertuples() if r.lo90 * r.hi90 > 0]
        print(f"{s}: impact {sub.beta.iloc[0]:+.3f}, "
              f"largest {sub.loc[i, 'beta']:+.3f} at h={int(sub.loc[i, 'horizon'])}, "
              f"band off zero at h={sig}")
    print(f"n per regression: {lp.n.max()} (h=0) down to {lp.n.min()} (h={H})")


if __name__ == "__main__":
    main()
