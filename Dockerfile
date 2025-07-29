FROM --platform=linux/amd64  python:3.11-slim as dev

ENV PYTHONUNBUFFERED=1 \
    TZ=Europe/Oslo \
    # pip:
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    # uv:
    UV_VERSION=0.7.15 \
    # pipx:
    PIPX_BIN_DIR=/opt/pipx/bin \
    PIPX_HOME=/opt/pipx/home \
    # venv
    VIRTUAL_ENV=/venv \
    PATH="/opt/pipx/bin:/venv/bin:$PATH"

RUN apt-get update && apt-get install -y \
    default-jre \
      && python -m pip install --upgrade pip pipx \
      && pipx install "uv==$UV_VERSION" \
      && uv --version \
    # Cleaning cache:
      && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
      && apt-get clean -y && rm -rf /var/lib/apt/lists/*

WORKDIR /project/libecalc/

COPY ./pyproject.toml ./uv.lock ./

# Building all dependencies first to get a python environment we can use for dev
RUN python3 -m venv $VIRTUAL_ENV && uv sync --locked

FROM dev AS build

COPY . .
RUN python3 -m venv $VIRTUAL_ENV && uv sync --locked

WORKDIR /project/libecalc/src/


FROM dev as dist

ARG ECALC_USER=1000
ARG ECALC_GROUP=1000
ARG ECALC_VERSION=0.0.0

RUN pip install 'wheel==0.37.1'

COPY . .

RUN mkdir /dist

# Set version in pyproject.toml, needed to update nightly version. Already done by release-please otherwise.
RUN poetry version $ECALC_VERSION

# Finally build the libecalc package
RUN uv build
RUN cp dist/*.whl /dist/
RUN chown -R $ECALC_USER:$ECALC_GROUP /dist/

USER $ECALC_USER
