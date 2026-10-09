# GitHub publication status

This branch currently contains only a partial publication of the local engineering workspace. The production app modules (`app/db.py`, `app/engine.py`, `app/agents.py`, `app/views.py`), tests, tools and full knowledge index have not all been published yet. Do not deploy or treat this repository snapshot as runnable.

The GitHub Actions workflow has run. `pip-audit` completed with “No known vulnerabilities found” for the dependency environment represented by the currently published `requirements.txt`; `compileall` completed but warned that `tools` and `tests` were missing. The test step failed because `tests/run_all.py` does not exist on this branch yet. This is a repository completeness failure, not a passing product test.

Local workspace verification is separately recorded in `RELEASE_STATUS.json`: 9 local test suites pass and compilation passes. These results are not equivalent to remote verification until the full source tree is published and Actions passes.

The regulatory dataset remains unpromoted. Seven curated legal binding-source spot checks do not establish full coverage of the 14,627 staged records; 14,620 records remain pending canonical reconciliation.
