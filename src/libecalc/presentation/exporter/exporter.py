from libecalc.presentation.exporter.handlers.handler import Handler


class Exporter:
    def __init__(self):
        """Iterate through all results and run all appliers. Gather those and return.

        TODO: Add support for pandas dataframe...
        """
        self.handlers: list[Handler] = []

    def export(self, grouped_row_based_data: dict[str, list[str]]):
        """:param grouped_row_based_data: grouped row based data. Each group will be dealt with separately with the handler
        :return:
        """
        for handler in self.handlers:
            handler.handle(grouped_row_based_data)

    def add_handler(self, handler: Handler):
        self.handlers.append(handler)


class ExporterRegistry:
    def __init__(self):
        pass

    def get(self, name: str) -> Exporter:
        """Iterate through all results and run all appliers. Gather those and return
        :param name:
        :return:
        """
        raise NotImplementedError
