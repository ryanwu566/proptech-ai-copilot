# NEW infrastructure image: extend the separately built Dockerfile.cloudrun image.
# SELFHOST_BACKEND_IMAGE must be a named local tag@sha256:digest or registry digest.
ARG SELFHOST_BACKEND_IMAGE
FROM ${SELFHOST_BACKEND_IMAGE}
USER root
RUN groupadd --gid 10001 proptech && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin proptech
COPY scripts/ops/selfhost_runtime.py /app/scripts/ops/selfhost_runtime.py
USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
ENTRYPOINT ["python", "scripts/ops/selfhost_runtime.py"]
CMD ["api"]
