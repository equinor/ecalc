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


YamlDict = _create_node_class(dict)
YamlList = _create_node_class(list)
