from libecalc.presentation.yaml.file_context import FileContext, FileMark


def _create_node_class(cls):
    class node_class(cls):  # type: ignore
        def __init__(self, *args, **kwargs):
            cls.__init__(self, *args)
            self.start_mark = kwargs.get("start_mark")
            self.end_mark = kwargs.get("end_mark")

        def __new__(self, *args, **kwargs):
            return cls.__new__(self, *args)

    node_class.__name__ = f"{cls.__name__}_node"
    return node_class


class YamlDict(dict):
    def __init__(self, *args, start_mark, end_mark, **kwargs):
        dict.__init__(self, *args)
        self.start_mark = start_mark
        self.end_mark = end_mark

    def __new__(cls, *args, **kwargs):
        return dict.__new__(cls, *args)

    def get_file_context(self) -> FileContext:
        start_mark = self.start_mark
        end_mark = self.end_mark
        return FileContext(
            start=FileMark(
                line_number=start_mark.line + 1,
                column_number=start_mark.column,
            ),
            end=FileMark(
                line_number=end_mark.line + 1,
                column_number=end_mark.column,
            ),
        )


YamlList = _create_node_class(list)
