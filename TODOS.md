# TODOS

## [P2] Add GitHub Actions CI workflow
- **What:** Create `.github/workflows/ci.yml` that runs pytest on push to main and PRs.
- **Why:** Catches broken tests before they land. Standard practice for any repo with tests.
- **Pros:** Automated safety net, enforces test discipline.
- **Cons:** ~30 lines YAML, minor maintenance.
- **Context:** Week 1 creates the workflows directory but leaves it empty. Add in Week 2 when real tests exist.
- **Effort:** S (CC: ~3 min)
- **Depends on:** Week 2 tests
- **Added:** 2026-05-13 (CEO review of Week 1)
