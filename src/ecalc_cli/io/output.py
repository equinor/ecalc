import json
import sys
from pathlib import Path
from typing import Dict, List

import libecalc.common.time_utils
from libecalc import dto
from libecalc.application.graph_result import GraphResult
from libecalc.common.run_info import RunInfo
from libecalc.common.time_utils import resample_time_steps
from libecalc.dto.result import EcalcModelResult as EcalcModelResultDTO
from libecalc.infrastructure.file_utils import OutputFormat, get_result_output
from libecalc.presentation.exporter.configs.configs import LTPConfig, STPConfig
from libecalc.presentation.exporter.exporter import Exporter
from libecalc.presentation.exporter.formatters.formatter import CSVFormatter
from libecalc.presentation.exporter.handlers.handler import MultiFileHandler
from libecalc.presentation.flow_diagram.EcalcModelMapper import EcalcModelMapper

from ecalc_cli.errors import EcalcCLIError


def write_output(output: str, output_file: Path = None):
    """Write output of eCalc run to either file (if output file path is specified) or to stdout.

    Args:
        output: Output of eCalc run
        output_file: Optional path to output file

    Returns:

    """
    if output_file is not None:
        with open(output_file, "w") as outfile:
            outfile.write(output)
    else:
        sys.stdout.write(output)


def write_json(
    results: EcalcModelResultDTO,
    output_folder: Path,
    name_prefix: str,
    run_info: RunInfo,
    date_format_option: int,
    simple_output: bool,
):
    """Create json of eCalc run results and write to file.

    Args:
        results: eCalc run results
        output_folder: Desired path to write results to
        name_prefix: Name of json file
        run_info: Metadata about eCalc run
        date_format_option: Date format, see DateFormat class for valid options
        simple_output: If true will create simple results, else full results are stored

    Returns:

    """
    json_v3_path = output_folder / f"{name_prefix}_v3.json"
    json_v3 = get_result_output(
        results=results,
        output_format=OutputFormat.JSON,
        simple_output=simple_output,
        date_format_option=date_format_option,
    )
    write_output(output=json_v3, output_file=json_v3_path)

    run_info_path = output_folder / f"{name_prefix}_run_info.json"
    run_info_json = run_info.json()
    write_output(output=run_info_json, output_file=run_info_path)


def write_ltp_export(
    results: GraphResult,
    frequency: libecalc.common.time_utils.Frequency,
    output_folder: Path,
    name_prefix: str,
):
    """Write LTP results to file.

    Args:
        results: eCalc run results
        frequency: Desired temporal resolution of results
        output_folder: Path to desired location of LTP results
        name_prefix: Name of LTP results file

    Returns:

    """
    export_tsv(
        config=LTPConfig,
        suffix=".ltp",
        frequency=frequency,
        name_prefix=name_prefix,
        output_folder=output_folder,
        results=results,
    )


def write_stp_export(
    results: GraphResult,
    frequency: libecalc.common.time_utils.Frequency,
    output_folder: Path,
    name_prefix: str,
):
    """Write STP results to file.

    Args:
        results: eCalc run results
        frequency: Desired temporal resolution of results
        output_folder: Path to desired location of STP results
        name_prefix: Name of STP results file

    Returns:

    """
    export_tsv(
        config=STPConfig,
        suffix=".stp",
        frequency=frequency,
        name_prefix=name_prefix,
        output_folder=output_folder,
        results=results,
    )


def export_tsv(
    config,
    suffix: str,
    frequency: libecalc.common.time_utils.Frequency,
    name_prefix: str,
    output_folder: Path,
    results: GraphResult,
):
    """Create tab-separated-values(tsv) file with eCalc model results.

    Args:
        config: Format of results file.
        suffix: File suffix
        frequency: Desired temporal resolution of results
        name_prefix: Name of file
        output_folder: Path to desired location of tsv file
        results: eCalc run results

    Returns:

    """
    resampled_timevector = resample_time_steps(results.timesteps, frequency)[
        :-1
    ]  # last step is always added as a STOP, and does infer the end of the time vector

    prognosis_filter = config.filter(frequency=frequency)
    result = prognosis_filter.filter(results, resampled_timevector)

    row_based_data: Dict[str, List[str]] = CSVFormatter(separation_character="\t").format(filtered_result=result)

    exporter = Exporter()
    exporter.add_handler(
        MultiFileHandler(
            path=output_folder,
            prefix=name_prefix,
            suffix=suffix,
            extension=".tsv",
        )
    )

    exporter.export(row_based_data)


def write_flow_diagram(model_dto: dto.Asset, result_options: dto.ResultOptions, output_folder: Path, name_prefix: str):
    """Write FDE diagram to file.

    Args:
        model_dto: eCalc model
        result_options: Result options specifying start, end and frequency
        output_folder: Desired output location of FDE diagram
        name_prefix: Name of FDE diagram file

    Returns:

    Raises:
        EcalcCLIError: If a OSError occurs during the writing of diagram to file.

    """
    flow_diagram = EcalcModelMapper.from_dto_to_fde(
        ecalc_model=model_dto,
        result_options=result_options,
    )
    flow_diagram_filename = f"{name_prefix}.flow-diagram.json" if name_prefix != "" else "flow-diagram.json"
    flow_diagram_path = output_folder / flow_diagram_filename
    try:
        flow_diagram_path.write_text(json.dumps([json.loads(flow_diagram.json(by_alias=True))]))
    except OSError as e:
        raise EcalcCLIError(f"Failed to write flow diagram: {str(e)}") from e
