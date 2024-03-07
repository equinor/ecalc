from pathlib import Path

import libecalc.common.time_utils
import libecalc.version
import typer
from libecalc.infrastructure.file_utils import (
    OutputFormat,
    get_component_output,
    get_result_output,
)
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel

from ecalc_cli.io.cache import Cache
from ecalc_cli.io.output import write_output
from ecalc_cli.logger import logger
from ecalc_cli.types import DateFormat, Frequency

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


@app.command("results")
def show_results(
    component_name: str = typer.Option(
        None,
        "-n",
        "--name",
        help="Filter the results to only show the component with this name",
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.JSON.value,
        "--output-format",
        help="Show the data in this format.",
    ),
    output_file: Path = typer.Option(
        None,
        "--file",
        help="Write the data to a file with the specified name.",
    ),
    output_folder: Path = typer.Option(
        Path.cwd(),
        "--output-folder",
        help="Output folder. Defaults to current working directory",
        show_default=False,
    ),
    detailed_output: bool = typer.Option(
        False,
        "--detailed-output",
        help="Output detailed output." " When False you will get basic energy usage and emissions results",
    ),
    date_format_option: DateFormat = typer.Option(
        DateFormat.ISO_8601.value,
        "--date-format-option",
        help='Date format option. 0: "YYYY-MM-DD HH:MM:SS" (Accepted variant of ISO8601), 1: "YYYYMMDD HH:MM:SS" (ISO8601), 2: "DD.MM.YYYY HH:MM:SS". Default 0 (ISO 8601)',
    ),
    output_frequency: Frequency = typer.Option(
        libecalc.common.time_utils.Frequency.NONE.name,
        "--output-frequency",
        "-f",
        help="Frequency of output. Options are DAY, MONTH, YEAR. If not specified, it will give"
        " time steps equal to the union of all input given with INFLUENCE_TIME_VECTOR set to True."
        " Down-sampling the result may lead to loss of data, and rates such as MW may not add up to cumulative values",
    ),
):
    """Show results. You need to run eCalc™ before this will be available."""
    cache = Cache(user_specified_output_path=output_folder)
    results = cache.load_results()
    run_info = cache.load_run_info()

    if run_info.version != libecalc.version.current_version():
        logger.warning(
            f"Your version of eCalc™ '{libecalc.version.current_version()}' is different to the one used to create the results '{run_info.version}'."
        )

    if output_frequency != Frequency.NONE:
        results_resampled = results.resample(libecalc.common.time_utils.Frequency[output_frequency.name])
    else:
        results_resampled = results.model_copy()

    component_name = component_name

    if component_name is None:
        # Default to full result if no specified component.
        text = get_result_output(
            results_resampled,
            output_format=output_format,
            simple_output=not detailed_output,
            date_format_option=int(date_format_option.value),
        )
    else:
        text = get_component_output(
            results_resampled,
            component_name,
            output_format=output_format,
            simple_output=not detailed_output,
            date_format_option=int(date_format_option.value),
        )

    write_output(text, output_file)
