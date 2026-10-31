# NEW infrastructure image: extend the separately built Dockerfile.cloudrun image.
# SELFHOST_BACKEND_IMAGE must be a named local tag@sha256:digest or registry digest.
ARG SELFHOST_BACKEND_IMAGE
FROM ${SELFHOST_BACKEND_IMAGE}
USER root
RUN set -eu; \
    if ! getent group 10001 >/dev/null; then groupadd --gid 10001 proptech; fi; \
    if ! getent passwd 10001 >/dev/null; then useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin proptech; fi
COPY scripts/ops/selfhost_runtime.py /app/scripts/ops/selfhost_runtime.py
COPY scripts/ops/professor_runtime_entrypoint.py /app/scripts/ops/professor_runtime_entrypoint.py
COPY services/selfhost_secret_files.py /app/services/selfhost_secret_files.py
COPY config/professor-server-credentials.json /app/config/professor-server-credentials.json
COPY config/hosted-environment-manifest.json /app/config/hosted-environment-manifest.json
USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
ENTRYPOINT ["python", "scripts/ops/selfhost_runtime.py"]
CMD ["api"]
