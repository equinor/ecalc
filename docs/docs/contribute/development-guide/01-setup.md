# Setup

```mdx-code-block
import TabItem from '@theme/TabItem';
import Tabs from '@theme/Tabs';
```

## Prerequisites

Basic prerequisites for local development are:
* *Linux or macOS*: For [Windows you can run Ubuntu or similar in WSL 2](https://docs.microsoft.com/en-us/windows/wsl/install-win10).
* *Git*: [git Docs](https://git-scm.com/book/en/v2/Getting-Started-About-Version-Control)
* *IDE*: It is recommended to use [PyCharm](https://www.jetbrains.com/pycharm/) as an Integrated Developer Environment.

:::info
It is possible to contribute to the project directly through GitHub in a web browser. This is great if you are only doing tiny changes.
:::

**Documentation Prerequisites:**
* *Node* incl. NPM package manager: Download from nodejs.org or use [nvm](https://github.com/nvm-sh/nvm)

**Developer requirements**:
To work with the entire project you'll need to install these tools. You can skip some, depending on your role:
* *Python >=3.8*: [Python homepage](https://www.python.org/)
* *Node* incl. NPM: [NodeJS](https://nodejs.org/en/download/) or [nvm](https://github.com/nvm-sh/nvm)
* *pre-commit*: [Pre-commit Docs](https://pre-commit.com/)
* *Snyk CLI* (Optional): [Snyk Docs](https://support.snyk.io/hc/en-us)
* *Azure CLI* (Optional): [Azure CLI Docs](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
* *Poetry*: [Poetry Docs](https://python-poetry.org/docs/)
* *Cypress* (Web): [Cypress Docs](https://docs.cypress.io/guides/getting-started/installing-cypress)
* *Docker and Docker Compose* (API & Web):
  * [Docker Engine Docs](https://docs.docker.com/engine/)
  * [Docker Compose Docs](https://docs.docker.com/compose/)

### Git
See our [Git Setup Guide](../guides/01-git.md#setting-up-git)

### Pre-commit
When contributing to this project, pre-commits are necessary, as they run certain tests, sanitisers, and formatters.
See [Pre-commit Intro Docs](https://pre-commit.com/#intro) for information about how to get going.

:::info
On commit locally, code is automatically formatted and checked for security vulnerabilities using pre-commit git hooks. 
A Pull Request created without pre-commit will likely fail build in [GitHub Actions Pipelines](https://github.com/equinor/ecalc-engine/actions)
:::
Quick summary:

#### Install pre-commit:

Using pip
```shell
pip install pre-commit
```

Using brew on macOS:
```shell
brew install pre-commit
```

#### Install Pre-commit hooks
The project provides a `.pre-commit-config.yaml` file that is used to set up git _pre-commit hooks_.
```shell
pre-commit install
```

#### Usage
Pre-commit will run on every commit, but can also be run manually on all files:
```shell
pre-commit run --all-files
```

Pre-commit tests can be skipped on commits with `git commit --no-verify`. Note, this will probably make the tests fail.
Please contact a developer if you have any issues.

### Python
Go to [Python.org](https://www.python.org/downloads/) and ensure that you have Python >=3.8. We currently recommend Python 3.11.

For macOS you can use [Brew Python@3.11](https://formulae.brew.sh/formula/python@3.11) or similar.

Regardless of how you install Python, make sure that you add the correct python binary to your $PATH. Here is a guide
on [How to Add Python to PATH](https://realpython.com/add-python-to-path/). Please reach out to one of the developers if you have trouble.


:::tip
To check which python version you have, run:
```shell
python --version
```
:::

### Poetry
See [Poetry Docs](https://python-poetry.org/docs/) for guide on how to get going. See ci-requirements.txt for version requirement.

We recommend using [pipx](https://python-poetry.org/docs/#installing-with-pipx) for installation.

See [Poetry Basic Usage](https://python-poetry.org/docs/basic-usage/) for an introduction.

### NodeJS & NPM
Please find the correct version of NodeJS matching ecalc-engine/projects/web/package.json at [NodeJS](https://nodejs.org/en/download/)
or install [Node Version Manager](https://github.com/nvm-sh/nvm)

### Cypress
See [Cypress Docs](https://docs.cypress.io/guides/getting-started/installing-cypress)

### Docker and Docker Compose
See [Docker - Getting Started](https://docs.docker.com/get-started/) and [Docker Compose - Overview](https://docs.docker.com/compose/)
for more details.


## Bootstrap the environment
As a full stack developer you need to do the following steps in order to get started:

### 1. Clone this repo

```shell script
git clone git@github.com:equinor/ecalc-engine.git
cd ecalc-engine
```

> **Note**: All subsequent steps assumes you start in the root ecalc-engine/ path.

### 2. Set environmental variables

Required environment variables for docker containers. Copy from the template and edit in your favourite editor.

```shell script
cd tools/devcalc
poetry install
poetry run devcalc env bootstrap
poetry run devcalc env mode OFFLINE
```

> **Note**: if you run on MacOS you need to leave the uid and gid at 502:1000 or something similar.

> **Note**: Replace OFFLINE with ONLINE to run the project in online-mode.

### 3. Post checkout

Navigate to ecalc-engine/bin and trigger the post-checkout.sh-script. This will build API stubs and install web 
dependencies.

```
cd bin
./post-checkout.sh
```

If you're _not_ running linux, web dependencies must be installed via docker to ensure the Linux environment is used. 

```
cd main
docker-compose run web npm install
```

### 4. Generate  HTTPS certificates
Then we must generate certificates for https:

```shell script
cd projects/oauth2-proxy
openssl req  -nodes -new -x509  -keyout server.key -out server.cert
sudo chown 2000:2000 server.*
```

> **Note**: oauth2_proxy runs with uid,gid 2000

### 5. Set ownership of files in main/data/files
Make a folder main/data/files if it does not exist.
Then we need to set ownership of the folder.
user id and group id should be the same as *ECALC_USER* and *ECALC_GROUP*:

```shell script
sudo chown $(id -u):$(id -g) main/data/files
```

### 6. Set correct project structure
Set correct project structure in PyCharm; `settings > project structure`,
set the folowing paths as source root:
- *projects/engine*
- *projects/cli*
- *projects/api*
- *projects/web/src*
- *libraries/libecalc/common*
- *libraries/libecalc/fixtures*
- *libraries/neqsim*

and changes in code should automatically be loaded. Only when external dependencies are changed you need to rebuild.

### 7. Run WebApp in docker with docker-compose

*ALWAYS* run our apps with the `docker compose` command, since we then will automatically
inject with environmental variables from the .env file.

```shell script
cd ../main
docker compose up -d
```

NOW you should have set up the development project successfully! See below for more details on the development workflow.
