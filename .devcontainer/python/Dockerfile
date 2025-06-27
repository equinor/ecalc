ARG VARIANT="3.11-bookworm"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}


ARG DEBIAN_FRONTEND=noninteractive
ARG UV_VERSION=0.7.15
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

# Python and poetry installation
RUN echo $(which python) && echo $(which python3)  \
    && python3 -m pip install --upgrade pip pipx \
    && pipx install "uv==${UV_VERSION}" \
    && pip install pre-commit \
    && uv --version \
    && pre-commit --version

# Set workdir to ecalc project
WORKDIR /workspaces/ecalc

# Copy essential file (devcontainer setup takes care of other files)
COPY pyproject.toml uv.lock ./

# Install poetry environment without root package
RUN uv sync --locked