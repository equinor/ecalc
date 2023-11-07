import io
import os
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List

from libecalc.presentation.exporter.handlers.handler import (
    FileHandler,
    MultiFileHandler,
    MultiStreamHandler,
    StreamHandler,
)


class TestHandlers(unittest.TestCase):
    def setUp(self):
        self.my_grouped_row_based_data: Dict[str, List[str]] = {
            "installation a": ["dates\tcol1\tcol2", "2020.01.01\t1.0\t3.2", "2021.01.01\t2.0\t4.2"],
            "installation b": ["dates\tcol1\tcol2", "2020.01.01\t2.0\t2"],
        }

    def test_stream_handler_defaults(self):
        my_stream: io.StringIO = io.StringIO()
        my_stream_handler: StreamHandler = StreamHandler(my_stream)
        my_stream_handler.handle(self.my_grouped_row_based_data)

        my_stream_value = my_stream.getvalue()

        assert (
            my_stream_value
            == """dates\tcol1\tcol2
2020.01.01\t1.0\t3.2
2021.01.01\t2.0\t4.2
dates\tcol1\tcol2
2020.01.01\t2.0\t2
"""
        )

    def test_stream_handler_with_names(self):
        my_stream: io.StringIO = io.StringIO()
        my_stream_handler: StreamHandler = StreamHandler(my_stream, emit_name=True)
        my_stream_handler.handle(self.my_grouped_row_based_data)

        my_stream_value = my_stream.getvalue()

        assert (
            my_stream_value
            == """
installation a

dates\tcol1\tcol2
2020.01.01\t1.0\t3.2
2021.01.01\t2.0\t4.2

installation b

dates\tcol1\tcol2
2020.01.01\t2.0\t2
"""
        )

    def test_multi_stream_handler(self):
        my_streams: Dict[str, io.StringIO] = {}
        my_stream_handler: MultiStreamHandler = MultiStreamHandler(my_streams)
        my_stream_handler.handle(self.my_grouped_row_based_data)

        assert len(my_streams) == 2
        assert (
            my_streams["installation a"].getvalue()
            == """dates\tcol1\tcol2
2020.01.01\t1.0\t3.2
2021.01.01\t2.0\t4.2
"""
        )
        assert (
            my_streams["installation b"].getvalue()
            == """dates\tcol1\tcol2
2020.01.01\t2.0\t2
"""
        )

    def test_file_handler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            my_file_handler: FileHandler = FileHandler(
                path=Path(tmpdir), prefix="haha", suffix="test", extension=".csv"
            )
            my_file_handler.handle(self.my_grouped_row_based_data)

            with open(os.path.join(tmpdir, "hahatest.csv")) as read_file:
                assert (
                    read_file.read()
                    == """dates\tcol1\tcol2
2020.01.01\t1.0\t3.2
2021.01.01\t2.0\t4.2
dates\tcol1\tcol2
2020.01.01\t2.0\t2
"""
                )

    def test_multi_file_handler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            my_file_handler: MultiFileHandler = MultiFileHandler(
                path=Path(tmpdir), prefix="haha", suffix=".test", extension=".csv"
            )
            my_file_handler.handle(self.my_grouped_row_based_data)

            with open(os.path.join(tmpdir, "haha.installation a.test.csv")) as read_file:
                assert (
                    read_file.read()
                    == """dates\tcol1\tcol2
2020.01.01\t1.0\t3.2
2021.01.01\t2.0\t4.2
"""
                )
            with open(os.path.join(tmpdir, "haha.installation b.test.csv")) as read_file:
                assert (
                    read_file.read()
                    == """dates\tcol1\tcol2
2020.01.01\t2.0\t2
"""
                )
