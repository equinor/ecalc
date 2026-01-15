from __future__ import annotations


class StreamPort:
    def __init__(
        self,
        is_inlet_port: bool,
        connected_to_stage_no: int = 0,
    ):
        self.is_inlet_port = is_inlet_port
        self.connected_to_stage_no = connected_to_stage_no
