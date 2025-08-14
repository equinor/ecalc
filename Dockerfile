FROM --platform=linux/amd64  python:3.11-slim AS dev

COPY --from=ghcr.io/astral-sh/uv:0.7.15 /uv /uvx /bin/


ENV PYTHONUNBUFFERED=1 \
    TZ=Europe/Oslo \
    # pip:
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

RUN apt-get update && apt-get install -y \
    default-jre \
    # Cleaning cache:
      && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
      && apt-get clean -y && rm -rf /var/lib/apt/lists/*

COPY . project/libecalc

WORKDIR /project/libecalc/

COPY ./pyproject.toml ./uv.lock ./

# Building all dependencies first to get a python environment we can use for dev
RUN uv sync --locked

FROM dev AS build

COPY . .
RUN uv sync --locked

WORKDIR /project/libecalc/src/


FROM dev AS dist

ARG ECALC_USER=1000
ARG ECALC_GROUP=1000
ARG ECALC_VERSION=0.0.0

COPY . .

RUN mkdir -p /dist

# Set version in pyproject.toml, needed to update nightly version. Already done by release-please otherwise.
RUN uv version $ECALC_VERSION

# Finally build the libecalc package
RUN uv build
RUN cp dist/*.whl /dist/
RUN chown -R $ECALC_USER:$ECALC_GROUP /dist/

USER $ECALC_USER
