from datetime import datetime
from pathlib import Path

import libecalc.common.time_utils
import libecalc.version
import typer
from libecalc.common.run_info import RunInfo
from libecalc.core.ecalc import EnergyCalculator
from libecalc.core.graph_result import GraphResult
from libecalc.input.model import YamlModel
from libecalc.output.utils.file_utils import OutputFormat, get_result_output

from ecalc_cli.errors import EcalcCLIError
from ecalc_cli.io.cache import Cache
from ecalc_cli.io.output import (
    write_flow_diagram,
    write_json,
    write_ltp_export,
    write_output,
    write_stp_export,
)
from ecalc_cli.logger import logger
from ecalc_cli.types import DateFormat, Frequency


def run(
    model_file: Path = typer.Argument(
        ...,
        help="The Model YAML-file specifying time series inputs,"
        " facility inputs and the relationship between energy consumers.",
    ),
    output_frequency: Frequency = typer.Option(
        libecalc.common.time_utils.Frequency.NONE.name,
        "--output-frequency",
        "-f",
        "--outputfrequency",
        help="Frequency of output. Options are DAY, MONTH, YEAR. If not specified, it will give"
        " time steps equal to the union of all input given with INFLUENCE_TIME_VECTOR set to True."
        " Down-sampling the result may lead to loss of data, and rates such as MW may not add up to cumulative values",
    ),
    csv: bool = typer.Option(
        True,
        "--csv",
        "-c",
        help="Toggle output of csv data.",
    ),
    json: bool = typer.Option(
        False,
        "--json",
        help="Toggle output of json output.",
    ),
    output_folder: Path = typer.Option(
        None,
        "--output-folder",
        "-o",
        "--outputfolder",
        help="Outputfolder. Defaults to output/ relative to the yml setup file",
        show_default=False,
    ),
    name_prefix: str = typer.Option(
        None,
        "--name-prefix",
        "-n",
        "--nameprefix",
        help="Name prefix for output data. Defaults to name of setup file.",
    ),
    ltp_export: bool = typer.Option(
        False,
        "--ltp-export",
        help="In addition to standard output, a specific Long Term Prognosis (LTP) file "
        "will be provided for simple export of LTP relevant data (Tabular Separated Values).",
    ),
    stp_export: bool = typer.Option(
        False,
        "--stp-export",
        help="In addition to standard output, a specific Short Term Prognosis (STP) file "
        "will be provided for simple export of STP relevant data (Tabular Separated Values).",
    ),
    flow_diagram: bool = typer.Option(
        False,
        "--flow-diagram",
        help="Output the input model formatted to be displayed in a custom flow diagram format in JSON",
    ),
    detailed_output: bool = typer.Option(
        False,
        "--detailed-output",
        "--detailedoutput",
        help="Output detailed output."
        " When False you will get basic results such as energy usage, power, time vector.",
    ),
    date_format_option: DateFormat = typer.Option(
        DateFormat.ISO_8601.value,
        "--date-format-option",
        help='Date format option. 0: "YYYY-MM-DD HH:MM:SS" (Accepted variant of ISO8601), 1: "YYYYMMDD HH:MM:SS" (ISO8601), 2: "DD.MM.YYYY HH:MM:SS". Default 0 (ISO 8601)',
    ),
):
    """CLI command to run a ecalc model."""
    if output_folder is None:
        output_folder = model_file.parent / "output"

    if name_prefix is None:
        name_prefix = model_file.stem

    output_frequency = libecalc.common.time_utils.Frequency[output_frequency.name]

    run_info = RunInfo(version=libecalc.version.current_version(), start=datetime.now())
    logger.info(f"eCalc™ simulation starting. Running {run_info}")
    validate_arguments(model_file=model_file, output_folder=output_folder)

    model = YamlModel(path=model_file, output_frequency=output_frequency)

    if (flow_diagram or ltp_export) and (model.start is None or model.end is None):
        logger.warning(
            "When using Flow Diagram or Long Term Prognosis export, START and END should be specified in YAML to make sure you get the intended period as output. See documentation for more information."
        )

    if flow_diagram:
        write_flow_diagram(
            model_dto=model.dto,
            result_options=model.result_options,
            output_folder=output_folder,
            name_prefix=name_prefix,
        )

    energy_calculator = EnergyCalculator(graph=model.graph)
    consumer_results = energy_calculator.evaluate_energy_usage(model.variables)
    emission_results = energy_calculator.evaluate_emissions(
        variables_map=model.variables,
        consumer_results=consumer_results,
    )
    results_core = GraphResult(
        graph=model.graph,
        consumer_results=consumer_results,
        variables_map=model.variables,
        emission_results=emission_results,
    )

    run_info.end = datetime.now()

    cache = Cache(user_specified_output_path=output_folder)
    cache.write_run_info(run_info)
    cache.write_results(
        results=results_core,
        component_dto=model.dto,
    )

    output_prefix: Path = output_folder / name_prefix

    results_dto = results_core.get_asset_result()

    if output_frequency != Frequency.NONE:
        # Note: LTP can't use this resampled-result yet, because of differences in methodology.
        results_resampled = results_dto.resample(output_frequency)
    else:
        results_resampled = results_dto.copy()

    if csv:
        csv_data = get_result_output(
            results=results_resampled,
            output_format=OutputFormat.CSV,
            simple_output=not detailed_output,
            date_format_option=int(date_format_option.value),
        )
        write_output(output=csv_data, output_file=output_prefix.with_suffix(".csv"))

    if json:
        write_json(
            results=results_resampled,
            output_folder=output_folder,
            name_prefix=name_prefix,
            run_info=run_info,
            date_format_option=int(date_format_option.value),
            simple_output=not detailed_output,
        )

    if ltp_export:
        write_ltp_export(
            results=results_core,
            output_folder=output_folder,
            frequency=output_frequency,  # Keep until alternative export option is in place (e.g. stp-export)
            name_prefix=name_prefix,
        )

    if stp_export:
        write_stp_export(
            results=results_core,
            output_folder=output_folder,
            frequency=output_frequency,  # Keep until alternative export option is in place (e.g. stp-export)
            name_prefix=name_prefix,
        )

    logger.info(f"eCalc™ simulation successful. Duration: {run_info.end - run_info.start}")


def validate_arguments(model_file: Path, output_folder: Path):
    """Helper function used to validate the CLI run command arguments.

    Args:
        model_file:
        output_folder:

    Returns:

    Raises:
        EcalcCLIError: If one of the arguments are invalid

    """
    if not model_file.is_file():
        raise EcalcCLIError(f"Setup file: {model_file.absolute()}: no such file")

    if not output_folder.parent.is_dir():
        raise EcalcCLIError(
            f"Output path {output_folder} not valid. Please specify an existing path or the name of a new folder in an existing path"
        )

    if not output_folder.is_dir():
        output_folder.mkdir()
