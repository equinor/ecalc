from pathlib import Path

import typer

import libecalc.version
from ecalc_cli.commands import show
from ecalc_cli.commands.run import run
from ecalc_cli.commands.selftest import selftest
from ecalc_cli.logger import CLILogConfigurator, LogLevel, logger
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.validation_errors import DataValidationError

app = typer.Typer(name="ecalc")

app.command()(run)
app.add_typer(show.app, name="show", help="Command to show information in the model or results.")
app.command(help="Test that eCalc has been successfully installed")(selftest)


def version_callback(value: any):
    """Typer helper function to print current version of libecalc.

    Args:
        value:

    Returns:

    """
    if value:
        print(f"eCalc\u2122 Version: {libecalc.version.current_version()}")
        raise typer.Exit()


@app.callback()
def argument_callback(
    log_level: LogLevel = typer.Option(
        LogLevel.INFO.value,
        "--log",
        help="Set the loglevel.",
    ),
    log_folder: Path = typer.Option(None, "--log-folder", help="Store log files in a folder"),
    version: bool = typer.Option(
        None,
        "--version",
        help="Show current eCalc\u2122 version.",
        callback=version_callback,
    ),
):
    """Args:
        log_level: Log level of the CLI logger, defaults to INFO
        log_folder: Path to location of log files
        version: Option to show libecalc version.

    Returns:

    """
    cli_log_configurator = CLILogConfigurator()
    cli_log_configurator.set_loglevel(log_level)

    if log_folder:
        if not log_folder.exists():
            logger.error(
                f"Path and/or folder to log-file {str(log_folder)} does not exist. Log will only be written to terminal."
            )
        else:
            cli_log_configurator.set_log_path(log_folder)


def main():
    """Main function to start the CLI.

    Returns:

    Raises:
        DataValidationError: Is raised for invalid Yaml models.

    """
    try:
        logger.info("Logging started")
        app()
    except ModelValidationException as mve:
        logger.error(str(mve))
    except DataValidationError as de:
        logger.error(de.extended_message)
    except Exception as e:
        logger.exception("An unexpected error occurred when running eCalc")  # in order to write to log
        raise e  # in order for Typer to catch it and prettyprint it


if __name__ == "__main__":
    main()
