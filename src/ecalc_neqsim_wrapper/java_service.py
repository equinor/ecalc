import logging
import os
from os import path
from typing import Self

from py4j.java_gateway import JavaGateway

from ecalc_neqsim_wrapper.exceptions import NeqsimError

_logger = logging.getLogger(__name__)


_local_os_name = os.name
_colon = ":"
if _local_os_name == "nt":
    _colon = ";"


class NeqsimGatewayError(NeqsimError): ...


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
    try:
        return JavaGateway.launch_gateway(classpath=classpath, die_on_exit=False, javaopts=[f"-Xmx{maximum_memory}"])
    except ValueError as e:
        msg = f"Could not launch java gateway: {str(e)}"
        _logger.error(msg)
        raise NeqsimGatewayError(msg) from e


class NeqsimService:
    """NOTE: Do not instantiate this class directly. Use it as a context manager, like:

    with NeqsimService() as neqsim_service:
        ...
    """

    ref_counter: int = 0
    service_instance: Self | None = None

    def __init__(self):
        raise RuntimeError("Do not instantiate this class directly. Use it as a context manager.")

    @classmethod
    def get_neqsim_service(cls, maximum_memory: str = "4G") -> "NeqsimService":
        if cls.ref_counter == 0:
            cls.service_instance = cls.__new__(cls)
            cls.service_instance._initialize(maximum_memory)
        return cls.service_instance

    def _initialize(self, maximum_memory: str = "4G"):
        self._gateway = _start_server(maximum_memory=maximum_memory)
        _logger.info(
            f"Started neqsim process with PID '{self._gateway.java_process.pid}' "
            f"on port '{self._gateway.gateway_parameters.port}'."
        )

    def __enter__(self):
        return self.get_neqsim_service(maximum_memory="4G")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__class__.ref_counter -= 1
        if self.__class__.ref_counter == 0:
            self._shutdown()

    def get_neqsim_module(self):
        return self._gateway.jvm.neqsim

    def _shutdown(self):
        _logger.info(
            f"Killing neqsim process with PID '{self._gateway.java_process.pid}' "
            f"on port '{self._gateway.gateway_parameters.port}'"
        )
        # Shutdown gateway, connections ++
        try:
            self._gateway.shutdown()
        except Exception:
            _logger.exception("Java gateway close failed")
        finally:
            self.__class__.service_instance = None

    # @classmethod
    # def get_neqsim_service(cls) -> "NeqsimService":
    #     try:
    #         return cls.service_instance
    #     except LookupError as e:
    #         raise ValueError("Java gateway must be set up") from e
