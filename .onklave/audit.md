# Template audit

- **Last audited:** 2026-08-04
- **Audited by:** Onklave platform maintenance (automated, Claude Code)
- **Next review due:** 2026-11-04 (quarterly, or sooner on a dependency alert)

## Why this file exists
So we know when this template was last deliberately checked, and what was true at
the time. Apps are generated from this repo — stale or vulnerable dependencies
here propagate to every app created from it.

## Scope of this audit
- **Does it actually work:** fresh virtualenv, real `pip install -e '.[dev]'`, real
  `pytest`, real `docker build`, and a real container run probed over HTTP
  (`/healthz`, `/`, and `PORT` injection).
- **Dependency currency and vulnerabilities:** direct and transitive Python
  dependencies, checked with `pip-audit` and `pip list --outdated`.
- **Container security posture:** base image currency and patch level, OS-package
  CVEs in the built image (`trivy`), non-root execution verified at runtime (not
  just declared), `.dockerignore` correctness.
- **Committed secrets:** pattern scan across the full git history, all refs.
- **FastAPI-specific defaults:** CORS configuration, `/docs` + `/openapi.json`
  exposure, request body size limits, error-response verbosity, response headers.

Not in scope: application logic beyond the two template routes, authentication
(the template ships none by design), and the `onklave.yaml` deploy manifest, which
was written and verified in a previous pass and was deliberately not touched.

## Verification run
All commands run on macOS 15 (arm64), host Python 3.13.11, Docker Engine 27.4.0.

| Check | Command | Result |
|---|---|---|
| Create virtualenv | `python3.13 -m venv .venv` | Pass — Python 3.13.11 |
| Install project + dev extras | `pip install -e '.[dev]'` | Pass — 27 packages, editable build of `app-0.1.0` |
| Test suite | `pytest -q` | **Pass — 2 passed**, 0 warnings (was 2 passed / 1 deprecation warning before this audit) |
| Dependency vulnerability audit | `pip-audit -r <frozen deps>` | Pass — `No known vulnerabilities found` (run before *and* after changes) |
| Outstanding upgrades | `pip list --outdated` | Pass — only `pip` itself and `pydantic_core` 2.46.4→2.47.0, which is pinned transitively by `pydantic` 2.13.4 and not ours to bump |
| Container image build | `docker build -t tf-audit:final .` | Pass — multi-stage build succeeded |
| Container health route | `docker run -p 18003:8000 …` + `curl /healthz` | Pass — `200` `{"status":"ok"}` |
| Container root route | `curl /` | Pass — `{"service":"onklave-fastapi-service","message":"Hello from Onklave"}` |
| `$PORT` injection honoured | `docker run -e PORT=9111 …` + `curl /healthz` | Pass — `{"status":"ok"}` on 9111 |
| Non-root execution (runtime) | `docker exec … id` | Pass — `uid=10001(appuser) gid=10001(appuser)` |
| Python version in image | `docker exec … python -V` | Pass — `Python 3.13.14` (latest 3.13 patch) |
| Image OS CVE scan | `trivy image --severity HIGH,CRITICAL` | 19 HIGH + 4 CRITICAL, **0 with a fix available** — see Finding 3 |
| CORS behaviour | `curl -X OPTIONS -H 'Origin: https://evil.example' …` | Pass — `405`, no `Access-Control-Allow-Origin` header returned |
| Docs/OpenAPI exposure | `curl -o /dev/null -w '%{http_code}' /docs /openapi.json` | `200` / `200` — publicly reachable, see Finding 4 |
| Committed secrets | `git grep -InE '(api[_-]?key\|secret\|password\|token\|BEGIN .*PRIVATE KEY\|AKIA…\|ghp_\|sk-…)' $(git rev-list --all)` | Pass — no matches anywhere in history |
| Files ever committed | `git log --all --diff-filter=A --name-only` | Pass — only the 10 expected template files |

Docker was available, so the image build **was** actually run and the resulting
container **was** actually served and probed. Nothing in this table is inferred.

## Dependency status
Dependencies were previously declared **completely unconstrained** (`fastapi`,
`uvicorn[standard]`, `pytest`, `httpx` with no version specifiers). A side effect
is that the install already resolved to the newest release of everything, so
there was **no backlog of missing security upgrades** — but that was luck, not
policy, and it is exactly the problem fixed below.

Resolved versions, before → after:

| Package | Before | After | Note |
|---|---|---|---|
| fastapi | 0.141.1 (unconstrained) | 0.141.1 (`>=0.141.1,<1.0`) | Latest release; now floored + capped |
| uvicorn[standard] | 0.52.1 (unconstrained) | 0.52.1 (`>=0.52.1,<1.0`) | Latest release; now floored + capped |
| starlette | 1.3.1 (transitive) | 1.3.1 | Latest; already on the 1.x major |
| pydantic | 2.13.4 (transitive) | 2.13.4 | Latest; **already v2 — no v1→v2 migration is outstanding** |
| pydantic-core | 2.46.4 (transitive) | 2.46.4 | 2.47.0 exists but is pinned by pydantic 2.13.4 |
| pytest | 9.1.1 (unconstrained) | 9.1.1 (`>=9.1.1,<10`) | Latest; now floored + capped |
| httpx (dev) | 0.28.1 | **removed** | Replaced — see below |
| httpx2 (dev) | — | 2.9.1 (`>=2.9.1,<3.0`) | starlette's TestClient now requires it; plain httpx is deprecated there |

**Upgraded / changed:**
- Added version floors and major-version ceilings to all four declared
  dependencies. Patch and minor security fixes still flow in automatically; a
  surprise major release can no longer break newly generated apps.
- Swapped the dev-only HTTP backend `httpx` → `httpx2`, clearing a live
  deprecation warning on the template's own test path (Finding 2).
- Container base image `python:3.12-slim` → `python:3.13-slim` (Finding 8).

**Deliberately NOT upgraded:**
- **pydantic v1 → v2:** not applicable. The template is already on pydantic 2.13.4;
  there is no v1 code anywhere in it. No migration cost, nothing to do.
- **pydantic-core 2.46.4 → 2.47.0:** transitively pinned by pydantic; forcing it
  would fight the resolver for no benefit. It will arrive with the next pydantic
  release.
- **Base image → alpine or distroless:** would eliminate all 23 HIGH/CRITICAL OS
  CVEs, and was verified to build and run, but is a platform-wide glibc/musl
  decision. Left for a human — see Finding 3.
- **Python 3.14:** 3.14 is current, but 3.13 is the safer default for a template
  whose generated apps will pull arbitrary third-party wheels. No CVE difference
  between them (measured, see Finding 3).

## Findings

1. **MEDIUM — Dependencies were entirely unpinned (fixed).** `fastapi`,
   `uvicorn[standard]`, `pytest` and `httpx` carried no version constraints at
   all. Every app generated from this template resolved whatever happened to be
   newest on PyPI at generation time, so two apps generated a month apart get
   different dependency trees, and any breaking major release silently breaks
   both newly generated apps and their Docker builds — with no signal from this
   repo. This is the highest-leverage issue found, precisely because it is a
   template. **Action taken:** added floors + major ceilings (see Dependency
   status). Tests and image build re-verified afterwards.

2. **MEDIUM — Test suite sat on a deprecated, soon-to-break code path (fixed).**
   starlette 1.3.1 emitted `StarletteDeprecationWarning: Using httpx with
   starlette.testclient is deprecated; install httpx2 instead`. `TestClient` is
   the only thing the template's tests use, so when starlette removes httpx
   support the template's test suite — and that of every app generated from it —
   stops working. **Action taken:** dev dependency `httpx` → `httpx2` 2.9.1.
   Verified: 2 passed, warning gone, no other change required.

3. **MEDIUM — Base image carries 23 unfixable HIGH/CRITICAL OS CVEs (recorded,
   not fixed).** `trivy` reports 19 HIGH + 4 CRITICAL in the Debian 13 (trixie)
   base, and **zero of them have a fixed version available** — they cannot be
   patched away by rebuilding or by `apt upgrade`. They are concentrated in
   `perl-base`, `util-linux` and `ncurses` (e.g. CVE-2026-13221, CVE-2026-42496,
   CVE-2026-8376) — packages the service never invokes at runtime, so real
   exploitability is low, but they will show up in any customer's image scan.
   Measured, not assumed: the count is **identical** on `python:3.12-slim`,
   `3.13-slim` and `3.14-slim`, so no Python version bump helps.
   `python:3.13-alpine` scans **0 HIGH/CRITICAL** and I verified it builds, runs,
   serves `/healthz`, and still runs as uid 10001 — at roughly half the size
   (141MB vs 272MB). **Not applied:** switching Debian→Alpine changes the C
   library from glibc to musl for every generated app, which can force
   source builds for third-party wheels that ship no musl binaries. That is a
   platform-wide default worth deciding deliberately, not a side effect of an
   audit. **Recommended action:** a human decides slim vs alpine vs distroless
   across all Onklave templates at once.

4. **LOW — `/docs`, `/redoc` and `/openapi.json` are publicly exposed (recorded,
   deliberately not changed).** Confirmed `200` with no authentication against a
   running container. This is the FastAPI default and is genuinely useful in a
   template, but a deployed customer app publishes its complete API surface —
   every route, parameter and schema — to anyone who finds the URL.
   **Not changed**, per the standing instruction not to alter the app's public
   behaviour unilaterally. **Recommended action:** a human decides whether the
   template should ship these gated behind an environment variable
   (e.g. `docs_url=None if os.environ.get("ENV") == "production" else "/docs"`),
   which would be a one-line change in `src/app/main.py`.

5. **LOW — No request body size limit.** Neither FastAPI nor uvicorn caps request
   body size by default, so a large POST is buffered by the worker. The correct
   place to enforce this is the ingress, not the app. **Recommended action:** the
   Onklave platform should set a default
   `nginx.ingress.kubernetes.io/proxy-body-size` for rendered app ingresses
   rather than each template solving it. No change made here.

6. **LOW — `server: uvicorn` response header.** Every response advertises the
   server stack, which is minor information disclosure that assists
   fingerprinting. Fixable with `--no-server-header` on the uvicorn command.
   **Not applied** — it alters response headers for every generated app for
   marginal benefit; flagged for the same batch decision as Finding 4.

7. **INFO — uvicorn runs without `--proxy-headers`.** Behind the Onklave ingress,
   client IPs in application logs will be the proxy's address rather than the
   real client. This is the *safe* default: enabling proxy headers without a
   correctly scoped `--forwarded-allow-ips` would let callers spoof
   `X-Forwarded-For`. Noted so nobody "fixes" it carelessly. No change made.

8. **INFO — Base image was one Python minor behind (updated).** `python:3.12-slim`
   was current and supported (security fixes until Oct 2028) and at its latest
   patch, so this was not a defect. Bumped to `python:3.13-slim` anyway to extend
   the support runway for apps generated from this template, after verifying the
   full stack installs, tests pass, and the image builds, runs and serves. Note
   this yields **no** CVE reduction (see Finding 3) — it is a longevity change.
   `requires-python` remains `>=3.12`, so the template still supports 3.12 for
   local development.

**Checked and clean — no action needed:**
- **CORS is not permissive.** No `CORSMiddleware` is configured at all, and a
  cross-origin preflight from `https://evil.example` returns no
  `Access-Control-Allow-Origin` header. Secure by default.
- **Non-root execution genuinely works.** Not merely a `USER` directive: verified
  at runtime as `uid=10001(appuser)`.
- **No secrets committed.** Pattern scan across every commit on every ref found
  nothing, and the only files ever added are the 10 expected template files.
- **Error responses do not leak internals.** `debug` is not enabled and no custom
  exception handler echoes internals; FastAPI returns generic JSON
  (`{"detail":"Not Found"}`) with tracebacks going to logs only.
- **`.dockerignore` is correct.** It excludes `.git`, `.env*`, virtualenvs,
  caches and `tests`, and correctly keeps `README.md`, which `pyproject.toml`
  references (a build would fail without it). Independently, the Dockerfile's
  `COPY` statements are explicit — only `pyproject.toml`, `README.md` and `src`
  reach the image — so nothing extraneous can leak in even by accident.
- **No dependency CVEs.** `pip-audit` clean before and after the changes.

## Changes made in this audit
- `pyproject.toml`: added version floors and major-version ceilings to
  `fastapi`, `uvicorn[standard]` and `pytest`.
- `pyproject.toml`: replaced the dev dependency `httpx` with `httpx2>=2.9.1,<3.0`,
  clearing the starlette `TestClient` deprecation.
- `Dockerfile`: base image `python:3.12-slim` → `python:3.13-slim` in both the
  build and final stages.
- Added this file (`.onklave/audit.md`).
- No application code was changed. `onklave.yaml` was not touched.

## Open items
1. **Decide the container base image across all templates (Finding 3).** Alpine
   removes all 23 HIGH/CRITICAL OS CVEs and halves image size, and was verified
   working here — but it means musl instead of glibc for every generated app.
   This should be one deliberate decision applied consistently to every Onklave
   template, not made per-template.
2. **Decide whether generated apps should expose `/docs` and `/openapi.json` in
   production (Finding 4).** Currently they are public. If the answer is no, the
   fix is a one-line change and should land in every language template at once.
   Bundle Finding 6 (`--no-server-header`) into the same decision.
3. **Set a platform-level ingress request body size limit (Finding 5)** rather
   than expecting each template to handle it.
4. **Consider a scheduled dependency alert.** This audit found no vulnerabilities,
   but it only holds as of 2026-08-04. Because the template previously had no
   version constraints, nothing here would have surfaced a bad release — the new
   ceilings help, but an automated weekly `pip-audit` against the templates would
   catch issues before the next quarterly review.
5. **Optional operational nicety, not applied to keep this diff tight:** setting
   `PYTHONUNBUFFERED=1` in the Dockerfile makes application logs appear promptly
   in Kubernetes instead of sitting in a stdout buffer. Worth adding to all
   templates if the platform team agrees.
