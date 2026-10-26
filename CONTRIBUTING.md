# Contributing

Questions, error reports and suggestions are welcome as
[GitHub issues](https://github.com/milinpatel07/lidar-performance-target-applicability/issues). Please use the
templates: an error report names what you ran, what you expected and what happened; a question names the page or file
it refers to.

## What can change and what cannot

- **The package, the browser pages and the documentation** (`package/`, `site/`, `docs/`, `tests/`) can be improved.
  The statistics of the package must stay equal to those of `case_study/experiments/m1_range_kitti.py`;
  `package/tests/` checks this.
- **The recorded results and the experiment scripts of the case study** (`case_study/results/`,
  `case_study/experiments/`) are the record of the paper and are not changed. Their SHA-256 values are recorded in
  `provenance.json` and checked by `case_study/checks/check_recorded_results.py`. A different analysis belongs in a new
  folder with its own provenance, labelled as such.

## Checks before a pull request

From the repository root with Python 3.10 and the pinned environment:

```bash
pip install -r case_study/environment/requirements.txt pytest==9.1.1
pip install ./package
python -m pytest package/tests
python tests/check_links.py
cd case_study && python reproduce_paper.py --no-latex
```

GitHub Actions runs these and the remaining checks on every push and pull request
([`.github/workflows/checks.yml`](.github/workflows/checks.yml)).

## Licences

Contributions to code are licensed under the MIT licence ([`LICENSE`](LICENSE)); contributions to results, data files
and documentation under CC BY-NC-SA 4.0 ([`LICENSE-results`](LICENSE-results)).
