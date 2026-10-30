# Local ML valuation runbook

This capability estimates reported gross transfer consideration per registered
building ping. It is explicitly separate from `/valuation/estimate`; it does not
replace comparable-sales valuation. Whole-dwelling interests and parking-exclusive
prices are unverified. All estimates are non-actionable observational outputs.

The implementation is also registered in `backend.api_main`. The accepted Stage 2
container is deliberately left running with its existing image. A one-worker
loopback companion on `127.0.0.1:8081` exposes the new routes without restarting
healthy port 8080. It requires no database connection, secret or external provider.
No public listener, reverse-proxy change or deployment is authorized here.

## Start and verify

The final `reports/professor-stage3-ml/acceptance.json` records the exact immutable
artifact path, model version and manifest pin. Runtime environment contains only:

```text
VALUATION_ML_ARTIFACT_DIR=/home/andy/proptech-model-artifacts/<model-version>
VALUATION_ML_MANIFEST_SHA256=<exact manifest SHA256>
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
```

The nonsecret activation file `.local/stage3/inference.env` holds the concrete
artifact and pin for the completed run. To run in the foreground from the repo:

```bash
set -a
source .local/stage3/inference.env
set +a
.venv/bin/python scripts/ops/serve_valuation_ml.py
```

Do not start a second listener if port 8081 is occupied. Inspect the existing
`GET /valuation/ml/v1/status` model version and process before any replacement.
The completed unattended session records its companion PID and logs under
`.local/stage3/`; these are local runtime files, never credentials or Git artifacts.
To stop the companion, verify the recorded PID command is exactly this Python
entrypoint, then send TERM to that process only. Never stop the Stage 2 API to
train or activate this companion.

```bash
curl --fail http://127.0.0.1:8081/health
curl --fail http://127.0.0.1:8081/valuation/ml/v1/status
curl --fail http://127.0.0.1:8080/health
```

`/docs` and `/openapi.json` on the companion document the DTO and endpoint. Model
loading is lazy and single-slot. A missing configuration returns 503; missing,
corrupt, incompatible or incorrectly pinned files return a sanitized 503. Load
failure is cached until process restart. No fallback model, demo estimate, network
request or online training is attempted. Files are size-bounded and hash-verified
before native text parsing; pickle is never loaded.

One request may load/predict at a time; concurrent work returns 429 with
`Retry-After: 1`. The companion additionally caps Uvicorn concurrency at eight and
uses the application's body-size/deadline middleware. Each prediction is a single
row with one native CPU thread. Training uses a separate process with two CPU
threads at reduced priority. Default main-app import works without ML packages;
only configured inference requires the isolated ML environment.

## Reproduce admission and fitting

Use the pinned environment in
`reports/professor-stage3-ml/environment.lock.txt`, Python version from the model
metadata, and a fresh private output/work directory. Do not install system-wide.
The full artifact verifier is bounded and read-only; SQLite uses
`mode=ro&immutable=1` and `query_only=ON`. It needs no source mount or serving DB.

```bash
.venv/bin/python -B scripts/ml/prepare_historical_transactions.py verify \
  --artifact /home/andy/proptech-ml-data/plvr-history/bccf2ec1bc19110b9f55e35c3eaec284c2ad57a97318acea7381c5be5002ccee \
  > .local/stage3/verification-new.json

.venv/bin/python scripts/ml/train_stage3.py prepare \
  --dataset /home/andy/proptech-ml-data/plvr-history/bccf2ec1bc19110b9f55e35c3eaec284c2ad57a97318acea7381c5be5002ccee \
  --verification .local/stage3/verification-new.json \
  --work /home/andy/proptech-ml-data/stage3/<fresh-run>

.venv/bin/python scripts/ml/train_stage3.py train \
  --work /home/andy/proptech-ml-data/stage3/<fresh-run> \
  --output-parent /home/andy/proptech-model-artifacts
```

Preparation writes compact memory-mapped arrays, hashes and a completed
`prepared.json`. An incomplete preparation is rebuilt from the immutable input;
a complete one is reused only if its contract, code and array hashes agree.
Candidate native models/results and final fit checkpoint avoid repeating completed
training after an interruption. Keep work directories private: they contain
address/road hashes used only for grouped evaluation. Never put them in Git.

Before a training phase, resource guards require at least 2 GiB available RAM and
8 GiB free disk. Watch `/proc/meminfo`, `free -h`, `df -h` and process RSS during
long work. A guard failure stops the job; do not lower the threshold. Recheck live
8080 health and resume only after resources are safe. Pre-existing full swap is
recorded separately from this process's RSS.

## Promotion and rollback

Artifact directories are immutable with hashes, JSON contracts, native text model,
preprocessing, evaluation, provenance and package versions. Keep the previous
directory. A deliberate activation changes the configured directory **and** exact
manifest pin, then restarts only the companion. Verify status and deterministic
requests before considering any later main-API integration. Roll back by selecting
the previous pair. Never overwrite a model directory or refit during requests.

To use these routes in the Stage 2 container later requires a reviewed image with
the new code, pinned ML dependencies, read-only artifact mount and two nonsecret
variables. This session does not rebuild or replace that healthy container.
Completing an independently validated PIT/whole-dwelling product requires source
evidence and a new target/admission review; changing runtime flags cannot provide
that evidence.

The bounded-v1 closure retains this exact model artifact and does not require
training, dataset rebuild or new weights. The API purpose envelope now permits
only `requested_value_basis=reported_transfer` and exposes its evidence limits in
`scope`; it leaves the fitted `Subject`/feature contract untouched. When deploying
this envelope update, restart only the user-owned 8081 companion after verifying
its recorded PID/command, then verify unchanged model pin, prediction values and
8080 health. This is not authorization for public deployment or frontend work.
