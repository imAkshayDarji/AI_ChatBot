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
- **Status:** PROMOTED to Week 2 scope (accepted via CEO review cherry-pick)

## [P2] Add Redis-backed distributed rate limiting
- **What:** Replace in-memory rate limiting with Redis-backed rate limiting via slowapi + Redis backend.
- **Why:** In-memory rate limiting doesn't work across multiple Railway instances. If the backend scales to 2+ containers, rate limits are per-container, not global.
- **Pros:** Production-grade rate limiting. Works across multiple instances.
- **Cons:** Adds Redis as a dependency. Slightly more complex configuration.
- **Context:** Week 2 adds simple in-memory rate limiting on login. This upgrades it to distributed.
- **Effort:** S (CC: ~5 min)
- **Priority:** P2
- **Depends on:** Redis instance on Railway (Week 6)
- **Added:** 2026-05-13 (CEO review of Week 2)

## [P3] Add password reset flow
- **What:** Password reset endpoint that generates a time-limited reset token, sends it via email, and allows setting a new password.
- **Why:** Admin lockout is a real operational risk. If the seed-generated password is lost, the only recovery is re-running the seed script or direct DB manipulation.
- **Pros:** Self-service password recovery. Standard for any admin panel.
- **Cons:** Requires an email service (SendGrid, Mailgun, or SMTP). Adds a `password_reset_tokens` table.
- **Context:** Week 2 builds auth but no reset mechanism. The seed script auto-generates passwords.
- **Effort:** M (CC: ~30 min)
- **Priority:** P3
- **Depends on:** Email service integration (post-MVP)
- **Added:** 2026-05-13 (CEO review of Week 2)
