import json
from pathlib import Path

import typer

from ecalc_cli.io.output import write_output
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset

app = typer.Typer()


@app.command("yaml")
def show_yaml(
    model_file: Path = typer.Argument(
        ...,
        help="YAML file specifying time series inputs, facility inputs and the relationship between energy consumers.",
    ),
    output_file: Path = typer.Option(
        None,
        "--file",
        help="Write the data to a file with the specified name.",
    ),
):
    """Show yaml model. This will show the yaml after processing !include."""
    model_filepath = model_file
    with open(model_filepath) as model_file:
        read_model = PyYamlYamlModel.dump_and_load_yaml(
            ResourceStream(name=model_file.name, stream=model_file), base_dir=model_filepath.parent
        )
        write_output(read_model, output_file)


@app.command("schema")
def show_schema(
    output_file: Path | None = typer.Option(
        None,
        "--file",
        help="Write the schema to a file with the specified name. If not specified, it will print to stdout.",
    ),
):
    write_output(json.dumps(YamlAsset.model_json_schema(by_alias=True), indent=2), output_file)
