import libecalc.version
from ecalc_cli.logger import logger
from ecalc_neqsim_wrapper import NeqsimService


def selftest_java() -> bool:
    """Check java installation.

    Returns:
        bool: True if Java is installed correctly, False otherwise.

    """
    try:
        with NeqsimService():
            logger.debug("SUCCESS: Java seems to be correctly installed!")
            return True
    except Exception:
        logger.error(
            "Java does not seem to be installed. eCalc will currently not work since NeqSim depends on Java. Please install. See instructions in documentation."
        )
        return False


def selftest():
    """Did eCalc install successfully? Go through a number of checkpoints and let user know what is ok and what is not."""
    logger.info(f"eCalc™ Version {libecalc.version.current_version()}")
    logger.info("Starting selftest ...")

    # 1. Check that Java is installed (required for NeqSim and fluid simulation), and Neqsim can be used
    java_installed = selftest_java()

    # TODO: 3. Run the simple test fixture, see that it works (1. from code 2. from yaml)

    if java_installed:
        logger.info("eCalc™ selftest done successfully.")
    else:
        logger.error("eCalc™ selftest done with errors. See descriptions above.")
