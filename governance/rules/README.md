# Quality rule registry

QualityRule records specify GX expectation names and parameters, associated asset/field and severity. Seed definitions are in `backend/app/services/seed.py`; execution is in `backend/app/quality/service.py`.

The rules validate identifiers, required customer metadata, ISO countries, risk ratings, required dates and nonnegative amounts. `docs/data-quality.md` explains observed scoring and distinguishes rule coverage, strict expectation success and row quality.
