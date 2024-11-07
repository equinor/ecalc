import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

logging.getLogger("faker").setLevel(logging.ERROR)  # faker spams the log in debug.


class OneLineExceptionFormatter(logging.Formatter):
    def formatException(self, exc_info):
        """Format an exception so that it prints on a single line."""
        result = super().formatException(exc_info)
        return repr(result)  # or format into one line however you want to

    def format(self, record):
        s = super().format(record)
        if record.exc_text:
            s = s.replace("\n", "") + "|"
        return s


logging_format = OneLineExceptionFormatter("%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s")

file_handler = RotatingFileHandler(Path(__file__).parent / ".log", maxBytes=1000, backupCount=0)
stream_handler = logging.StreamHandler()

file_handler.setFormatter(logging_format)
stream_handler.setFormatter(logging_format)

logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, stream_handler])


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path


@pytest.fixture(scope="session")
def monkeypatch_session(request):
    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()
