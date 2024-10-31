
# libecalc test directory

This directory contains a convenience simple `docker-compose.yml` to run tests in a docker
container for libecalc. The original reason behind this need is to run snapshot tests in an x86_64 environment,
since developer may run on ARM64 architecture. Some of the snapshot tests are architecture dependent, and 
running them on an ARM64 machine will result in different values than for x86_64. This is due to Delanay 
triangulation algorithm used in some of the compressor calculations.

## Running tests in Docker (STP/LTP snapshot tests)

Since running tests in a container is only required for some of the tests, the default setup is already
configured in *docker-compose.yml* file. To run tests, simply run (from test/ dir):

```bash
docker compose run test
```

or (since we currently only have one service, and default is to run the docker-snapshot test)

```bash
docker compose up
```

This will build the container and run the tests marked 'dockersnapshot'. If the snapshot has changed, it will fail with exit code 1, and
update snapshots. Rerun the test again, with the command above, to make sure it passes.

## Running tests locally (ie not docker)

Run all tests except the STP/LTP snapshot tests (for now), and skip future tests we need to run in Docker:

```
pytest [other_args] --snapshot-update -m "not dockersnapshot"
```

## Alternative test

If you want to run the dockersnapshot tests and update snapshots without docker compose, and ad-hoc, you can run the following command, from libecalc root:

```bash
docker run --rm -v .:/project/libecalc -w /project/libecalc -t $(docker build -q . -f Dockerfile --target build) poetry run pytest -m dockersnapshot --snapshot-update
```
