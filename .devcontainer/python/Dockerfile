ARG VARIANT="3.11-bookworm"
FROM mcr.microsoft.com/devcontainers/python:${VARIANT}


ARG DEBIAN_FRONTEND=noninteractive
ARG POETRY_VERSION=1.8.3
ARG POETRY_VIRTUALENVS_PATH
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

# Set poetry virtualenv path in writable dir outsde mounted workspace
ENV POETRY_VIRTUALENVS_PATH="$HOME/.venv"

# Python and poetry installation
RUN echo $(which python) && echo $(which python3)  \
    && python3 -m pip install --upgrade pip pipx \
    && pipx install "poetry==${POETRY_VERSION}" \
    && pip install pre-commit \
    && poetry --version \
    && pre-commit --version
