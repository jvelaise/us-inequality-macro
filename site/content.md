---
status: draft
title: Rising Income Inequality in the US
subtitle: What 78 years of data show, and what they can't tell us
---
<!--
HOW TO EDIT THIS FILE
* Each section starts with a line "## id | Heading". Keep the ids (the site
  places charts by id); change the headings and text freely.
* Numbers in {curly.braces} are filled in from the data by code/04_build_site.py.
  Do NOT type numbers by hand: use a placeholder so the site updates when the
  data does. The list of available placeholders is printed by:
      python code/04_build_site.py --list-facts
* While "status: draft" is set above, the site shows a DRAFT banner.
  Change it to "status: approved" only after you have checked every claim.
* Text under "drivers" comes from published research, NOT from this site's
  data. Check each citation before approving.
-->

## intro | The short version

US family incomes are close to the most unequal they have been since records began in {g.first_year}. The **Gini index**, the standard yardstick of income inequality, rose from **{g.low_value}** in {g.low_year} to **{g.last_value}** in {g.last_year}.

This site asks a narrower question we can actually test with data: **do the ups and downs of the economy (growth, inflation, government deficits) push inequality up or down?** They do, a little. But those effects are small next to the long rise, so the main explanation has to lie elsewhere.

## rise | Inequality bottomed out in {g.low_year} and has climbed since

From {g.first_year} to {g.low_year}, inequality drifted *down* by about {g.trend_before} points per decade. Since then it has risen by about **{g.trend_after} points per decade**, adding {g.rise_since_low} points in total. Every decade since the 1970s has averaged higher than the one before.

**How to read the Gini index:** 0 would mean every family has the same income; 100 would mean one family has all of it. Here a change of 1 point is meaningful.

**One jump is partly measurement.** The single biggest one-year increase (+{g.jump_size} points in {g.jump_year}) coincides with a change in how the Census Bureau collected income data, which by itself raised measured inequality. The long upward trend is clear with or without that year.

## cycle | Booms narrow inequality a little; inflation's effect flips over time

We tracked what happened to inequality in the eight years after a year when growth, inflation, or the federal budget balance was 1 percentage point higher than usual, comparing against what recent history would otherwise predict.

* **Faster growth narrows inequality for about four years.** A year of 1 point faster growth goes with a Gini {gdp.h0} points lower straight away, and {gdp.peak} points lower after {gdp.peak_h} years.
* **Inflation helps at first, then hurts.** Higher inflation goes with *lower* inequality in the first couple of years, but from about year {inf.flip_h} it goes with *higher* inequality, peaking at +{inf.peak} points after {inf.peak_h} years. Looking at a single year would make these two phases cancel out.
* **The federal deficit shows no reliable link** at most horizons. The one large estimate, at {fis.peak_h} years, rests on the least data and shouldn't carry weight.

Shaded bands show the range the true effect plausibly falls in (90% confidence). Where a band crosses zero, the data can't rule out "no effect".

## size | These effects are ripples on a rising tide

The largest effect we found, {gdp.peak} points from faster growth, is about **{gdp.share_pct}% of the {s.rise}-point rise** in inequality over {s.start}–{s.end}. The business cycle moves inequality around its trend; it does not explain the trend.

## drivers | So what does explain the long rise?

*This section summarises published research. It is **not** tested by this site's data.*

* **Technology and skills.** Demand for highly educated workers has outpaced supply, raising their pay relative to everyone else (Goldin & Katz, *The Race between Education and Technology*, 2008). Automation of routine tasks has also reduced wages for some groups (Acemoglu & Restrepo, *Econometrica*, 2022).
* **Fewer unions.** Union membership fell sharply after the 1970s, weakening a force that compressed wages (Western & Rosenfeld, *American Sociological Review*, 2011).
* **Pulling away at the top.** The share of income going to the top 1% has risen steeply since 1980, with changes in top tax rates and pay-setting as candidate causes (Piketty & Saez, *Quarterly Journal of Economics*, 2003).
* **Trade and globalisation.** Import competition, especially from China after 2000, cut manufacturing jobs and wages in exposed regions (Autor, Dorn & Hanson, *American Economic Review*, 2013).
* **Who lives with whom.** High earners increasingly marry each other, which widens gaps between families (Greenwood et al., *American Economic Review*, 2014).

## caveats | What this analysis can and can't tell us

* **Patterns, not proof.** The results show what tends to follow a year of faster growth or higher inflation. They don't prove the economy *caused* the change: inequality could affect growth, or something else could drive both.
* **Families only.** This Gini covers families and leaves out people living alone. The Census household measure (from 1967) runs a few points higher.
* **Limited data.** Annual data give {s.n} years ({s.start}–{s.end}), and only {s.n_min} observations at the 8-year horizon, so the estimates are imprecise.

## method | How this was made

1. Five data series downloaded from FRED (Federal Reserve Bank of St. Louis): the Census family Gini index, real GDP growth, CPI inflation, the federal surplus/deficit as a share of GDP, and unemployment.
2. Monthly series averaged to calendar years, using complete years only.
3. Local-projection regressions (Jordà 2005): for each horizon of 0–8 years, the change in the Gini regressed on the macro variable, controlling for two years of history in every variable. Sample sizes run from {s.n_max} observations down to {s.n_min}.
4. Every number on this page is computed by code from the saved data. Text was drafted with AI assistance and reviewed by the author.
