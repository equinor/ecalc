from pathlib import Path

import typer

from ecalc_cli.io.output import write_output
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel

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
