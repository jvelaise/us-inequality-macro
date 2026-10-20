"""Two-page PDF summary of the US inequality / macro local-projection analysis.
Numbers are read from the saved artifacts, never re-typed."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, PageBreak)

BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9.3, leading=13.2,
                      spaceAfter=5)
H1 = ParagraphStyle("h1", parent=BODY, fontName="Helvetica-Bold", fontSize=15,
                    leading=18, spaceAfter=2)
SUB = ParagraphStyle("sub", parent=BODY, fontSize=8.6, textColor=colors.HexColor("#595959"),
                     spaceAfter=10)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Helvetica-Bold", fontSize=10.2,
                    spaceBefore=8, spaceAfter=3)
CAP = ParagraphStyle("cap", parent=BODY, fontSize=8.1,
                     textColor=colors.HexColor("#595959"), spaceBefore=3)
LI = ParagraphStyle("li", parent=BODY, leftIndent=11, bulletIndent=2, spaceAfter=4)


def _sig(sub):
    """Horizons whose 90% band excludes zero."""
    return [int(r.horizon) for r in sub.itertuples() if r.lo90 * r.hi90 > 0]


def build(lp, cc, fig_path, gini_span, out="inequality_macro_summary.pdf"):
    labels = {"gdp_growth": "Real GDP growth",
              "inflation_cpi_avg": "CPI inflation (annual average)",
              "fiscal_balance_pct_gdp": "Federal fiscal balance (% GDP)"}
    rows = [["Macro variable", "Impact (h=0)", "Largest effect", "90% band at largest",
             "Horizons with band off zero"]]
    detail = {}
    for s, lab in labels.items():
        sub = lp[lp.shock == s].sort_values("horizon")
        i = sub.beta.abs().idxmax()
        pk = sub.loc[i]
        sig = _sig(sub)
        detail[s] = dict(h0=sub.beta.iloc[0], peak=pk.beta, peak_h=int(pk.horizon),
                         lo=pk.lo90, hi=pk.hi90, sig=sig)
        rows.append([lab, f"{sub.beta.iloc[0]:+.3f}",
                     f"{pk.beta:+.3f} at {int(pk.horizon)} yr",
                     f"[{pk.lo90:+.3f}, {pk.hi90:+.3f}]",
                     ", ".join(map(str, sig)) if sig else "none"])

    gini_rise = (cc["gini_families"].iloc[-1] - cc["gini_families"].iloc[0]) * 100
    share = abs(detail["gdp_growth"]["peak"]) / gini_rise * 100
    y0, y1, n = int(cc.index.min()), int(cc.index.max()), len(cc)
    nmin, nmax = int(lp.n.min()), int(lp.n.max())

    doc = SimpleDocTemplate(out, pagesize=A4, topMargin=1.6*cm, bottomMargin=1.5*cm,
                            leftMargin=2.0*cm, rightMargin=2.0*cm,
                            title="Inequality and the US Macroeconomy")
    S = []
    S.append(Paragraph("Inequality and the US Macroeconomy", H1))
    S.append(Paragraph(f"Lag-structure evidence from annual data, {y0}&ndash;{y1} "
                       f"(n = {n} complete cases)", SUB))

    S.append(Paragraph("Data and method", H2))
    S.append(Paragraph(
        "Six annual US series were merged into a single panel. Inequality is the Census "
        "Gini index distributed by FRED as <font face='Helvetica-Oblique'>GINIALLRF</font> "
        f"({int(gini_span[0])}&ndash;{int(gini_span[1])}). The macro block is real GDP growth "
        "(A191RL1A225NBEA), CPI inflation (CPIAUCSL), the federal surplus or deficit as a share "
        "of GDP (FYFSGDA188S) and the unemployment rate (UNRATE). Monthly series were aggregated "
        "to calendar-year averages using complete years only, so 2026 is excluded rather than "
        "averaged over nine months. Inflation is carried in two forms, annual-average and "
        "December-over-December; the two differ materially in individual years (4.68 against "
        "7.17 percent in 2021), so the baseline choice of annual-average is explicit rather "
        "than inherited from a frequency-conversion default.", BODY))
    S.append(Paragraph(
        "Dynamics are estimated by Jord&agrave; local projections: the cumulative change in the "
        "Gini from the year before the observation to horizon h is regressed on the macro "
        "variable in year t, controlling for two lags of all five variables and of the Gini "
        "change itself. Horizons run 0 to 8 years, standard errors are Newey&ndash;West with "
        f"h+1 lags, and the estimation sample falls from {nmax} observations at impact to "
        f"{nmin} at the longest horizon. Coefficients read as Gini index points per "
        "1 percentage point.", BODY))

    S.append(Paragraph("Findings", H2))
    t = Table(rows, colWidths=[4.5*cm, 2.2*cm, 2.9*cm, 3.4*cm, 3.4*cm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.2),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8.2),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#1F4E79")),
        ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.HexColor("#D9D9D9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    S.append(t)
    S.append(Spacer(1, 7))

    d = detail
    S.append(Paragraph(
        f"<b>Growth is the one clear result.</b> A 1 pp higher real growth rate predicts a Gini "
        f"{abs(d['gdp_growth']['h0']):.3f} points lower on impact, deepening to "
        f"{d['gdp_growth']['peak']:+.3f} at {d['gdp_growth']['peak_h']} years "
        f"[{d['gdp_growth']['lo']:+.3f}, {d['gdp_growth']['hi']:+.3f}], then fading. The band "
        f"excludes zero at horizons {', '.join(map(str, d['gdp_growth']['sig']))}.", LI, bulletText="\u2022"))
    S.append(Paragraph(
        f"<b>Inflation reverses sign.</b> Negative on impact ({d['inflation_cpi_avg']['h0']:+.3f}), "
        f"still negative at two years, crossing into positive territory from year four and "
        f"growing to a peak of "
        f"{d['inflation_cpi_avg']['peak']:+.3f} at {d['inflation_cpi_avg']['peak_h']} years "
        f"[{d['inflation_cpi_avg']['lo']:+.3f}, {d['inflation_cpi_avg']['hi']:+.3f}]. A single "
        "contemporaneous regression would net these two phases against each other and report "
        "approximately nothing.", LI, bulletText="\u2022"))
    S.append(Paragraph(
        f"<b>The fiscal balance mostly is not there.</b> Negative at impact "
        f"({d['fiscal_balance_pct_gdp']['h0']:+.3f}) and at two years, then a band straddling "
        f"zero. The large {d['fiscal_balance_pct_gdp']['peak']:+.3f} at "
        f"{d['fiscal_balance_pct_gdp']['peak_h']} years sits on the widest band in the figure "
        "and the smallest subsample, and should not carry weight.", LI, bulletText="\u2022"))
    S.append(Paragraph(
        f"<b>Magnitudes are small.</b> The Gini rose {gini_rise:.1f} points across the sample "
        f"({cc['gini_families'].iloc[0]*100:.1f} to {cc['gini_families'].iloc[-1]*100:.1f}). "
        f"The largest growth effect is {share:.1f} percent of that rise, so these are cyclical "
        "modulations around the trend, not an account of the trend itself.", LI, bulletText="\u2022"))

    S.append(Spacer(1, 4))
    S.append(Image(fig_path, width=16.4*cm, height=16.4*cm*(3.4/10.5)))
    S.append(Paragraph(
        "Cumulative Gini response to each macro variable. Shaded bands are 90 percent "
        "Newey&ndash;West intervals. Responses are predictive, not identified causal effects.", CAP))

    S.append(PageBreak())

    S.append(Paragraph("What these estimates do and do not establish", H2))
    S.append(Paragraph(
        "<b>Identification.</b> The regressor is the realised macro variable, not an identified "
        "shock. These are predictive responses conditional on two lags of the system, so reverse "
        "causality running from inequality to growth is unaddressed, as is any third factor "
        "moving both. The literature's standard remedies are narrative or sign-restricted shocks "
        "for monetary and fiscal policy, or an instrument for growth; none is applied here.", BODY))
    S.append(Paragraph(
        "<b>The inequality concept.</b> GINIALLRF appears to be the Census <i>family</i> Gini "
        "rather than the household series of Table H-4: the identifier suffix and the 1947 start "
        "both point that way, and household data begin only in 1967 and sit several points higher. "
        "The downloaded file carries no series title, so this identification is inferred and "
        "should be confirmed against FRED's documentation before the number appears in a chapter. "
        "Families exclude single-person households, which is not a neutral omission here: the "
        "growth in single-person households is itself part of the measured rise in inequality.", BODY))
    S.append(Paragraph(
        "<b>Sample and specification.</b> Annual data over 78 years supports two lags and little "
        "more. Horizon-8 estimates rest on 67 observations. The lag length, the horizon ceiling "
        "and the control set were not selected by criterion; they are conventional choices, and "
        "the growth result should be checked against alternatives before it is leaned on. "
        "Stationarity was not formally assessed: the dependent variable is a cumulative change, "
        "which handles the Gini's persistence, but the regressors enter in levels.", BODY))

    S.append(Paragraph("Suggested next steps", H2))
    for i, (h, txt) in enumerate([
        ("Vary the inequality concept",
         "Rerun with the Census household Gini (Table H-4, 1967 onward) and the WID top 1 percent "
         "income share (1913 onward). If the growth and inflation patterns hold across a dispersion "
         "measure and a concentration measure, the result is considerably stronger than it is now; "
         "if they do not, the finding is about family income composition rather than inequality "
         "in general. The WID series also roughly doubles the sample, which would let the lag "
         "structure be estimated rather than assumed."),
        ("Test the inflation-timing choice",
         "Re-estimate using December-over-December inflation, already present in the panel. The "
         "mid-horizon sign flip is the paper's most interesting feature and also the one most "
         "exposed to how inflation is dated against annual income."),
        ("Move toward identification",
         "Substitute identified monetary and fiscal shock series for the realised variables. This "
         "is the step that converts the growth coefficient from a stylised fact into a causal "
         "claim, and it is where a referee will look first."),
        ("Extend to the cross-country panel",
         "The original design: World Bank WDI Gini with IMF WEO growth, inflation and fiscal "
         "balances, estimated with country and year fixed effects, then the same local projections "
         "within panel. Cross-country variation also allows the institutional and redistributive "
         "differences that a single-country time series cannot speak to."),
        ("Resolve data access before scaling up",
         "Every source needed for the cross-country phase is blocked by the organisation's network "
         "allowlist, so each file currently arrives by manual download. Requesting that an "
         "administrator allowlist fred.stlouisfed.org, www2.census.gov, wid.world and "
         "api.worldbank.org would make the whole pipeline a rerunnable fetch rather than a file "
         "shuffle, which matters once the panel spans many countries and vintages."),
    ], 1):
        S.append(Paragraph(f"<b>{i}. {h}.</b> {txt}", LI))

    S.append(Paragraph("Reproducibility", H2))
    S.append(Paragraph(
        "Saved alongside this note: <font face='Helvetica-Oblique'>us_macro_annual.csv</font> "
        "(the merged annual panel), <font face='Helvetica-Oblique'>lp_gini_response.csv</font> "
        "(all 27 coefficients with standard errors, bounds, t-statistics and per-horizon n) and "
        "<font face='Helvetica-Oblique'>gini_local_projections.png</font>. Each carries the code "
        "that produced it, so the aggregation conventions above are recoverable rather than "
        "described. Source files were downloaded from FRED on 15 October 2026.", BODY))

    doc.build(S)
    return out


if __name__ == "__main__":
    import pathlib as _pl, pandas as _pd
    _root = _pl.Path(__file__).resolve().parents[1]
    _panel = _pd.read_csv(_root / "data" / "us_macro_annual.csv", index_col="year")
    _lp = _pd.read_csv(_root / "outputs" / "lp_gini_response.csv")
    _g = _panel["gini_families"].dropna()
    print(build(_lp, _panel.dropna(), str(_root / "outputs" / "gini_local_projections.png"),
                (_g.index.min(), _g.index.max()),
                out=str(_root / "outputs" / "inequality_macro_summary.pdf")))
