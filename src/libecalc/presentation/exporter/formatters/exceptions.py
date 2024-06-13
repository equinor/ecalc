class ColumnNotFound(Exception):
    def __init__(self, column_id):
        self.column_id = column_id
        super().__init__(f"Column with id '{column_id}' not found")


class RowNotFound(Exception):
    def __init__(self, row_id):
        self.row_id = row_id
        super().__init__(f"Row with id '{row_id}' not found")
