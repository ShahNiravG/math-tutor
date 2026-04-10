Scrape AMC 10 exam(s) from AoPS wiki into curated exam JSON files. Run from `/home/nshah/projects/math-tutor`.

Usage examples:
- Scrape all 2020–2025 exams (skips existing files): `/scrape-amc scrape-all math_tutor/challenges_src/curated/`
- Scrape a single exam by URL: `/scrape-amc scrape https://artofproblemsolving.com/wiki/index.php?title=2025_AMC_10B math_tutor/challenges_src/curated/2025-amc-10b.json`

After scraping, rebuild the site to pick up new exams:
```
source .env && .venv/bin/math-tutor-build-site --site-dir math_tutor/output/deploy/math_tutor/site
```

Run:
```
.venv/bin/python -m math_tutor.amc10_scraper $ARGUMENTS
```

Note: there is no venv entry point for this — always use `.venv/bin/python -m math_tutor.amc10_scraper`.

Report which exams were written or skipped, and any errors.
