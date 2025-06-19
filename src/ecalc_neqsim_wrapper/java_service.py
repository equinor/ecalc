import logging
from typing import Optional

from jneqsim import neqsim

_logger = logging.getLogger(__name__)


# Java process started explicitly, should only be used 'on-demand', not on import
_neqsim_service: Optional["NeqsimService"] = None


class NeqsimService:
    def __init__(self, maximum_memory: str = "4G"):
        global _neqsim_service
        _neqsim_service = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

    def get_neqsim_module(self):
        return neqsim

    def shutdown(self):
        pass


def get_neqsim_service():
    try:
        return _neqsim_service
    except LookupError as e:
        raise ValueError("Java gateway must be set up") from e
