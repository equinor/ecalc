# Testing

## Python libraries
For Python we use [Pytest](https://docs.pytest.org/). The libraries and CLI can run in their normal Python environments,
assuming that the environment is set up like described in [Development Setup Guide](01-setup.md):

Navigate to the part of the project you want to test, such as `ecalc-engine/libraries/libecalc/common/`

```shell
poetry shell
pytest run
```
It is also possible to run using PyCharm GUI, assuming that you have set up your environment correctly.

:::into
We use [pytest-snapshot](https://github.com/joseph-roitman/pytest-snapshot) to ensure some integration tests does not change
without us doing it on purpose. In order to update a snapshot test you will have to use `pytest --snapshot-update`. The tests
will fail if the result changes without updating the snapshot specifically.
:::
## Python APIs

For `ecalc-engine/projects/engine/` and `ecalc-engine/projects/api/` you will have to run the tests using Docker Compose.

If everything is set up correctly, then you can navigate to `ecalc-engine/main/` and run:

**Engine**
```shell
docker-compose run --rm engine-api poetry run pytest /projects/engine/tests
```

**API**
```shell
docker-compose run --rm backend poetry run pytest /projects/api/tests
```

:::note
This requires that Docker is running and that you have set up your environmental variables as seen in
[Setup Guide - Bootstrap the Environment](01-setup.md#bootstrap-the-environment).
:::
