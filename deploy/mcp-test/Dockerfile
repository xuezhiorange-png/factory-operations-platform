# syntax=docker/dockerfile:1
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY backend /app/backend
# Session CA is a build-only mount, never an image layer. Docker supplies its configured proxy.
RUN --mount=type=secret,id=build_ca,required=true \
    PIP_CERT=/run/secrets/build_ca python -m pip install --no-cache-dir /app/backend
COPY deploy/mcp-test /app/mcp-test
RUN chmod -R go+rX /app/backend /app/mcp-test
USER 10001:10001
ENTRYPOINT ["python", "/app/mcp-test/entrypoint.py"]
