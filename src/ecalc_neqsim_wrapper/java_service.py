import logging
import os
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from os import path
from typing import Optional, Self

from ecalc_neqsim_wrapper.exceptions import NeqsimError
from libecalc.common.errors.exceptions import ProgrammingError

_logger = logging.getLogger(__name__)

# Java process started explicitly, should only be used 'on-demand', not on import
# Either use NeqsimPy4JService or NeqsimJPypeService, cannot change once instantiated, ie the Python process lifetime
_neqsim_service: Optional["NeqsimService"] = None

_local_os_name = os.name
_colon = ":"
if _local_os_name == "nt":
    _colon = ";"


class NeqsimGatewayError(NeqsimError): ...


def _create_classpath(jars):
    """Create path to NeqSim .jar file"""
    resources_dir = path.dirname(__file__) + "/lib"
    return _colon.join([path.join(resources_dir, jar) for jar in jars])


def _start_server(maximum_memory: str = "4G") -> "JavaGateway":  #  type: ignore # noqa: F821
    """
    Start JVM for NeqSim Wrapper
    Returns: (int, Popen) port, process

    """
    jars = ["NeqSim.jar"]
    classpath = _create_classpath(jars)

    logging.getLogger("py4j").setLevel(logging.ERROR)
    try:
        from py4j.java_gateway import JavaGateway

        return JavaGateway.launch_gateway(classpath=classpath, die_on_exit=False, javaopts=[f"-Xmx{maximum_memory}"])
    except ValueError as e:
        msg = f"Could not launch java gateway: {str(e)}"
        _logger.error(msg)
        raise NeqsimGatewayError(msg) from e


class NeqsimService(AbstractContextManager, ABC):
    def __init__(self) -> None:
        raise ProgrammingError("Use factory() and initialize() to create an instance of NeqsimService.")

    @classmethod
    @abstractmethod
    def initialize(cls, maximum_memory: str = "4G") -> Self:
        """
        maximum_memory: Maximum memory for the Java process, only used for legacy Py4J implementation
        """
        ...

    @classmethod
    def instance(cls) -> "NeqsimService":
        try:
            global _neqsim_service
            if _neqsim_service is None:
                raise ProgrammingError("NeqsimService is not initialized. Initialize before use.")

            return _neqsim_service
        except LookupError as e:
            raise ValueError("Java gateway must be set up") from e

    @abstractmethod
    def __enter__(self) -> "NeqsimService": ...

    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback, /): ...

    @abstractmethod
    def get_neqsim_module(self): ...

    @staticmethod
    def factory(use_jpype: bool = False) -> type["NeqsimService"]:
        """
        Factory method to create NeqsimService instance
        Args:
            use_jpype: If True, use JPype implementation, otherwise use legacy Py4J implementation

        Returns: NeqsimService instance

        """
        if use_jpype:
            return NeqsimJPypeService
        else:
            return NeqsimPy4JService

    @abstractmethod
    def shutdown(self): ...


class NeqsimJPypeService(NeqsimService):
    """
    New version of NeqsimService using JPype, via JNeqsim
    Implemented by Neqsim Team
    """

    def __new__(cls, maximum_memory: str = "4G") -> "NeqsimJPypeService":
        instance = super().__new__(cls)
        return instance

    @classmethod
    def initialize(cls, maximum_memory: str = "4G") -> Self:
        _logger.info("NeqsimJPypeService.initialize() called")
        global _neqsim_service
        if _neqsim_service is None:
            # We are bypassing __init__ by calling __new__ directly instead
            _neqsim_service = cls.__new__(cls, maximum_memory=maximum_memory)
            return _neqsim_service

        if type(_neqsim_service) is not NeqsimJPypeService:
            raise ProgrammingError(
                "NeqsimService is already initialized with a different implementation, and can only be initialized once."
            )

        return _neqsim_service

    def get_neqsim_module(self):
        import jneqsim

        return jneqsim.neqsim

    def __enter__(self) -> "NeqsimService":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        No need to shutdown JPype, we will continue to use the same JVM instance
        for the lifetime of the Python process
        Args:
            exc_type:
            exc_val:
            exc_tb:

        Returns:

        """
        ...

    def shutdown(self): ...  # No shutdown for JPype, JVM will be reused for the lifetime of the Python process


class NeqsimPy4JService(NeqsimService):
    """
    Legacy version of NeqsimService using Py4J
    Implemented by eCalc Team
    """

    def __new__(cls, maximum_memory: str = "4G") -> "NeqsimPy4JService":
        instance = super().__new__(cls)
        instance._gateway = _start_server(maximum_memory=maximum_memory)
        _logger.info(
            f"Started neqsim process with PID '{instance._gateway.java_process.pid}' "
            f"on port '{instance._gateway.gateway_parameters.port}'"
        )
        return instance

    @classmethod
    def initialize(cls, maximum_memory: str = "4G") -> Self:
        _logger.info("NeqsimPy4JService.initialize() called")
        global _neqsim_service
        if _neqsim_service is None:
            # We are bypassing __init__ by calling __new__ directly instead
            _neqsim_service = cls.__new__(cls, maximum_memory=maximum_memory)
            return _neqsim_service

        if type(_neqsim_service) is not NeqsimPy4JService:
            raise ProgrammingError(
                "NeqsimService is already initialized with a different implementation, and can only be initialized once."
            )

        return _neqsim_service

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        We need to shutdown the Java process, since the instance will have information about the old
        port, which is not valid anymore. Also, we have observed memory leaks in the Java process,
        might be "just the way it works", but a quick fix is to restart the process for each run.
        Args:
            exc_type:
            exc_val:
            exc_tb:

        Returns:

        """
        self.shutdown()

    def get_neqsim_module(self):
        return self._gateway.jvm.neqsim

    def shutdown(self):
        """
        Exposed as public method for testing only. In production code use context manager.
        """
        _logger.info("NeqsimPy4JService.shutdown called")
        _logger.info(
            f"Killing neqsim process with PID '{self._gateway.java_process.pid}' on port '{self._gateway.gateway_parameters.port}'"
        )

        global _neqsim_service
        try:
            if type(_neqsim_service) is NeqsimPy4JService:
                _neqsim_service._gateway.shutdown()
                _neqsim_service._gateway = None
        except Exception:
            _logger.exception("Java gateway close failed")
        finally:
            _neqsim_service = None
