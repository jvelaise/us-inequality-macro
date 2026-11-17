# us-inequality-macro
CS193T project: rising US income inequality and the macroeconomy.

**Website:** `docs/index.html` (published with GitHub Pages; see below).

## What's here
| Path | What it is |
|---|---|
| `data/raw/` | FRED downloads (Gini, GDP growth, CPI, fiscal balance, unemployment) |
| `code/01_build_panel.py` | Raw files to annual panel `data/us_macro_annual.csv` |
| `code/02_estimate_and_plot.py` | Local projections: `outputs/lp_gini_response.csv` + figure |
| `code/03_build_report.py` | Two-page PDF summary |
| `code/04_build_site.py` | Website `docs/index.html`, built from the outputs + `site/content.md` |
| `site/content.md` | **All website text.** Edit this, not the HTML. |
| `notebooks/gini_coefficient.ipynb` | Explainer notebook for the Gini trend (runs in Colab) |
| `tests/` | Checks that the numbers, text and page agree |

## Rerun everything
```bash
pip install -r requirements.txt
bash run_all.sh
```
Each step stops with a clear message if something is wrong. Open `docs/index.html` to preview.

## Edit the website text
1. Edit `site/content.md`. Use `{placeholders}` for any number from the data
   (`python code/04_build_site.py --list-facts` lists them). Hand-typed numbers fail the tests.
2. `python code/04_build_site.py && python -m pytest -q`
3. When every claim is checked, change `status: draft` to `status: approved` to remove the DRAFT banner.

## Update the data
Download fresh CSVs from FRED into `data/raw/` (same file names), or set `REFRESH = True` in the
notebook in Colab, then `bash run_all.sh`. Review the diff of `site/content.md` claims before publishing.

## Publish (once)
GitHub repo **Settings → Pages → Build and deployment → Deploy from a branch → `main` / `/docs` → Save**.
The site appears at `https://jvelaise.github.io/us-inequality-macro/` a minute or two later.
