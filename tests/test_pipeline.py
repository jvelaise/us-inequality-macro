"""Checks for the data -> results -> website pipeline.   Run:  python -m pytest -q

Each test guards a specific way the site could silently show something wrong."""
import importlib.util
import json
import pathlib
import re

import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("site_build", ROOT / "code" / "04_build_site.py")
site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site)


@pytest.fixture(scope="module")
def built():
    facts, charts, checks, g, lp = site.compute_facts()
    meta, sections = site.parse_content(site.CONTENT.read_text())
    page = site.build_html(meta, sections, facts, charts, g, lp)
    return dict(facts=facts, charts=charts, checks=checks, meta=meta, sections=sections, page=page)


# --- data ------------------------------------------------------------------
def test_panel_is_complete_and_plausible():
    p = pd.read_csv(ROOT / "data" / "us_macro_annual.csv", index_col="year")
    cc = p.dropna()
    assert cc.index.min() == 1948 and len(cc) == cc.index.max() - cc.index.min() + 1, "gap in sample"
    assert p.gini_families.dropna().between(0.2, 0.7).all()
    assert p.unemployment_rate.dropna().between(0, 30).all()


def test_results_file_has_every_horizon():
    lp = pd.read_csv(ROOT / "outputs" / "lp_gini_response.csv")
    assert len(lp) == 27 and set(lp.horizon) == set(range(9))
    assert (lp.lo90 <= lp.beta).all() and (lp.beta <= lp.hi90).all()


# --- consistency between outputs -------------------------------------------
def test_site_numbers_match_notebook_summary(built):
    path = ROOT / "outputs" / "gini_summary.json"
    if not path.exists():
        pytest.skip("notebook summary not generated")
    nb, g = json.loads(path.read_text()), built["facts"]["g"]
    assert nb["low_year"] == g["low_year"] and nb["last_year"] == g["last_year"]
    assert f'{nb["last_value"]:.1f}' == g["last_value"]
    assert nb["largest_jump_year"] == g["jump_year"]


def test_claims_in_text_hold_in_data(built):
    # "Every decade since the 1970s has averaged higher than the one before."
    assert built["checks"]["decades_rising_since_1970s"]
    # "Faster growth narrows inequality": growth effect negative at impact and peak
    lp = pd.read_csv(ROOT / "outputs" / "lp_gini_response.csv")
    gdp = lp[lp.shock == "gdp_growth"]
    assert (gdp.beta.iloc[:5] < 0).all()
    # "Inflation helps at first, then hurts"
    inf = lp[lp.shock == "inflation_cpi_avg"].set_index("horizon").beta
    assert inf[0] < 0 and inf[5] > 0


# --- content file ------------------------------------------------------------
def test_unknown_placeholder_fails_loudly(built):
    with pytest.raises(KeyError, match="unknown placeholder"):
        site.fill("rose to {g.not_a_fact}", built["facts"])


ALLOWED_TYPED = {"0", "1", "2", "8", "90", "100", "1967", "1970s", "1980", "2000", "2005"}


def test_no_hand_typed_data_numbers_outside_research_section(built):
    """Numbers from the data must come in through {placeholders} so they update with it."""
    for sid, sec in built["sections"].items():
        if sid == "drivers":          # citations: years and journals, checked by a human
            continue
        text = site.PLACEHOLDER.sub("", sec["heading"] + "\n" + sec["md"])
        text = re.sub(r"(?m)^\s*\d+\.\s", "", text)   # numbered-list markers
        typed = set(re.findall(r"\d+(?:\.\d+)?s?", text)) - ALLOWED_TYPED
        assert not typed, f"section '{sid}' has hand-typed numbers {typed}; use a placeholder"


# --- rendered page -----------------------------------------------------------
def test_page_has_all_sections_and_charts(built):
    page = built["page"]
    for sid in site.REQUIRED_SECTIONS:
        assert f'<section id="{sid}">' in page
    for cid in ["chart-gini", "chart-lp-gdp", "chart-lp-inf", "chart-lp-fis", "chart-size"]:
        assert f'id="{cid}"' in page
    assert not re.search(r"\{[a-z]+\.[a-z0-9_]+\}", page), "unfilled placeholder"


def test_key_numbers_appear_on_page(built):
    f, page = built["facts"], built["page"]
    for v in [f["g"]["last_value"], f["g"]["low_value"], f["g"]["rise_since_low"], f["gdp"]["peak"]]:
        assert str(v) in page


def test_chart_data_is_consistent(built):
    m = re.search(r'id="chart-data">(.*?)</script>', built["page"], re.S)
    data = json.loads(m.group(1))
    assert len(data["gini"]["x"]) == len(data["gini"]["y"]) > 70
    for s in data["lp"].values():
        assert len(s["horizon"]) == 9


def test_draft_banner_follows_status(built):
    draft = built["meta"].get("status") != "approved"
    assert ("DRAFT" in built["page"]) == draft
