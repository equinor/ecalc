ARG VARIANT="3.12-bookworm"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}

COPY --from=ghcr.io/astral-sh/uv:0.7.15 /uv /uvx /bin/

ARG DEBIAN_FRONTEND=noninteractive
ENV USER=vscode

RUN DEBIAN_FRONTEND=noninteractive \
    && apt-get update \
    && apt-get install -y build-essential --no-install-recommends make \
        ca-certificates \
        git \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        wget \
        curl \
        llvm \
        libncurses5-dev \
        xz-utils \
        tk-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libffi-dev \
        liblzma-dev \
        default-jre

# Set non-root user
USER $USER
ENV HOME="/home/$USER"
ENV PATH="${HOME}/.local/bin:$PATH"

ENV PIP_DEFAULT_TIMEOUT=100

WORKDIR /project/libecalc

# Copy essential file (devcontainer setup takes care of other files)
COPY pyproject.toml uv.lock ./