import logging
import os
from os import path
from typing import Optional

from py4j.java_gateway import JavaGateway

_logger = logging.getLogger(__name__)


# Java process started explicitly, should only be used 'on-demand', not on import
_neqsim_service: Optional["NeqsimService"] = None


_local_os_name = os.name
_colon = ":"
if _local_os_name == "nt":
    _colon = ";"


def _create_classpath(jars):
    """Create path to NeqSim .jar file"""
    resources_dir = path.dirname(__file__) + "/lib"
    return _colon.join([path.join(resources_dir, jar) for jar in jars])


def _start_server(maximum_memory: str = "4G") -> JavaGateway:
    """
    Start JVM for NeqSim Wrapper
    Returns: (int, Popen) port, process

    """
    jars = ["NeqSim.jar"]
    classpath = _create_classpath(jars)

    logging.getLogger("py4j").setLevel(logging.ERROR)
    return JavaGateway.launch_gateway(classpath=classpath, die_on_exit=False, javaopts=[f"-Xmx{maximum_memory}"])


class NeqsimService:
    def __init__(self, maximum_memory: str = "4G"):
        global _neqsim_service
        self._gateway = _start_server(maximum_memory=maximum_memory)
        _logger.info(
            f"Started neqsim process with PID '{self._gateway.java_process.pid}' on port '{self._gateway.gateway_parameters.port}'"
        )
        _neqsim_service = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def get_neqsim_module(self):
        return self._gateway.jvm.neqsim

    def shutdown(self):
        global _neqsim_service
        _logger.info(
            f"Killing neqsim process with PID '{self._gateway.java_process.pid}' on port '{self._gateway.gateway_parameters.port}'"
        )
        # Shutdown gateway, connections ++
        try:
            self._gateway.shutdown()
        except Exception:
            _logger.exception("Java gateway close failed")
        finally:
            _neqsim_service = None


def get_neqsim_service():
    try:
        return _neqsim_service
    except LookupError as e:
        raise ValueError("Java gateway must be set up") from e
