"""GUI viewer for process solver events.

Visualizes the chronological event log produced by :class:`EventService`
during an :class:`OutletPressureSolver` run.

Usage::

    from libecalc.domain.process.process_solver.event_viewer import show_events

    events = EventService()
    # ... set up tracing and run a solve ...
    show_events(events, process_units=[choke, compressor_stage, ...])
"""

from __future__ import annotations

from collections.abc import Sequence

import FreeSimpleGUI as sg

from libecalc.domain.process.process_solver.event_service import (
    ConfigurationAppliedEvent,
    Event,
    EventService,
    StreamPropagatedEvent,
)
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_UNIT_TYPE_NAMES: dict[str, str] = {
    "CompressorStageProcessUnit": "Compressor",
    "CompressorTrainStageProcessUnit": "Compressor",
    "Choke": "Choke",
    "DirectMixer": "Mixer",
    "DirectSplitter": "Splitter",
    "TemperatureSetter": "TempSet",
    "LiquidRemover": "LiqRemov",
    "SpeedCompressorStage": "Compressor",
}


def _short_id(uid: object) -> str:
    """Return the last 8 hex chars of a UUID-like id."""
    return str(uid)[-8:]


def _unit_label(unit: ProcessUnit | ProcessSystem) -> str:
    cls = type(unit).__name__
    nice = _UNIT_TYPE_NAMES.get(cls, cls)
    return f"{nice}\n{_short_id(unit.get_id())}"


def _config_summary(cfg_value: object) -> str:
    if isinstance(cfg_value, SpeedConfiguration):
        return f"speed={cfg_value.speed:.2f}"
    if isinstance(cfg_value, RecirculationConfiguration):
        return f"recirc={cfg_value.recirculation_rate:.1f}"
    if isinstance(cfg_value, ChokeConfiguration):
        return f"dP={cfg_value.delta_pressure:.4f}"
    return str(cfg_value)


def _stream_summary(label: str, stream) -> list[str]:
    return [
        f"{label}:",
        f"  pressure     = {stream.pressure_bara:.4f} bara",
        f"  temperature  = {stream.temperature_kelvin:.2f} K",
        f"  std rate     = {stream.standard_rate_sm3_per_day:.2f} Sm3/d",
        f"  vol rate     = {stream.volumetric_rate_m3_per_hour:.4f} m3/h",
        f"  density      = {stream.density:.4f} kg/m3",
    ]


# ---------------------------------------------------------------------------
# Table data
# ---------------------------------------------------------------------------


def _build_table_data(events: list[Event]) -> list[list[str]]:
    rows: list[list[str]] = []
    for i, event in enumerate(events):
        if isinstance(event, ConfigurationAppliedEvent):
            cfg = event.configuration
            rows.append(
                [
                    str(i),
                    "Config",
                    _short_id(cfg.simulation_unit_id),
                    _config_summary(cfg.value),
                ]
            )
        elif isinstance(event, StreamPropagatedEvent):
            rows.append(
                [
                    str(i),
                    "Stream",
                    _short_id(event.process_unit_id),
                    f"P: {event.inlet_stream.pressure_bara:.2f} -> {event.outlet_stream.pressure_bara:.2f}",
                ]
            )
    return rows


# ---------------------------------------------------------------------------
# Detail text
# ---------------------------------------------------------------------------


def _detail_text(event: Event) -> str:
    lines: list[str] = []
    if isinstance(event, ConfigurationAppliedEvent):
        cfg = event.configuration
        lines.append("Configuration Applied")
        lines.append(f"  unit id: {cfg.simulation_unit_id}")
        lines.append(f"  value:   {_config_summary(cfg.value)}")
    elif isinstance(event, StreamPropagatedEvent):
        lines.append("Stream Propagated")
        lines.append(f"  unit id: {event.process_unit_id}")
        lines.append("")
        lines.extend(_stream_summary("Inlet", event.inlet_stream))
        lines.append("")
        lines.extend(_stream_summary("Outlet", event.outlet_stream))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Process system diagram on a Graph element
# ---------------------------------------------------------------------------

_BOX_W = 100
_BOX_H = 50
_GAP = 40
_MARGIN = 20
_ARROW_LEN = _GAP - 4


def _draw_process_diagram(
    graph: sg.Graph,
    units: Sequence[ProcessUnit | ProcessSystem],
    highlight_id: ProcessUnitId | None = None,
) -> None:
    graph.erase()
    x = _MARGIN
    y_mid = _MARGIN + _BOX_H // 2

    for i, unit in enumerate(units):
        is_active = highlight_id is not None and unit.get_id() == highlight_id
        fill = "#4a90d9" if is_active else "#d0d0d0"
        text_color = "#ffffff" if is_active else "#000000"

        top_left = (x, y_mid - _BOX_H // 2)
        bottom_right = (x + _BOX_W, y_mid + _BOX_H // 2)

        graph.draw_rectangle(top_left, bottom_right, fill_color=fill, line_color="#333333", line_width=2)
        graph.draw_text(
            _unit_label(unit),
            location=(x + _BOX_W // 2, y_mid),
            color=text_color,
            font=("Helvetica", 9),
        )

        # Arrow to next unit
        if i < len(units) - 1:
            arrow_start = (x + _BOX_W + 2, y_mid)
            arrow_end = (x + _BOX_W + _ARROW_LEN, y_mid)
            graph.draw_line(arrow_start, arrow_end, color="#555555", width=2)
            # Arrowhead
            graph.draw_polygon(
                [
                    arrow_end,
                    (arrow_end[0] - 6, arrow_end[1] - 4),
                    (arrow_end[0] - 6, arrow_end[1] + 4),
                ],
                fill_color="#555555",
            )

        x += _BOX_W + _GAP


def _canvas_size(n_units: int) -> tuple[int, int]:
    width = max(400, _MARGIN * 2 + n_units * _BOX_W + (n_units - 1) * _GAP)
    height = _MARGIN * 2 + _BOX_H
    return width, height


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------


def show_events(
    event_service: EventService,
    process_units: Sequence[ProcessUnit | ProcessSystem],
) -> None:
    """Open an interactive window visualizing the events collected by
    *event_service*.

    Args:
        event_service: The event service containing recorded events.
        process_units: The ordered list of process units in the system,
            used to draw the process diagram.
    """
    events = event_service.get_events()
    table_data = _build_table_data(events)
    headings = ["#", "Type", "Unit", "Summary"]

    canvas_w, canvas_h = _canvas_size(len(process_units))

    diagram = sg.Graph(
        canvas_size=(canvas_w, canvas_h),
        graph_bottom_left=(0, canvas_h),
        graph_top_right=(canvas_w, 0),
        background_color="#ffffff",
        key="-DIAGRAM-",
    )

    event_table = sg.Table(
        values=table_data,
        headings=headings,
        auto_size_columns=False,
        col_widths=[5, 8, 10, 40],
        justification="left",
        num_rows=min(25, max(10, len(table_data))),
        enable_events=True,
        enable_click_events=True,
        select_mode=sg.TABLE_SELECT_MODE_BROWSE,
        key="-TABLE-",
        expand_x=True,
        expand_y=True,
    )

    detail_box = sg.Multiline(
        default_text="Select an event to see details.",
        size=(60, 16),
        disabled=True,
        font=("Courier", 11),
        key="-DETAIL-",
        expand_x=True,
        expand_y=True,
    )

    layout = [
        [sg.Text("Process System", font=("Helvetica", 12, "bold"))],
        [diagram],
        [sg.HorizontalSeparator()],
        [
            sg.Column(
                [[sg.Text("Events", font=("Helvetica", 12, "bold"))], [event_table]],
                expand_x=True,
                expand_y=True,
            ),
            sg.VerticalSeparator(),
            sg.Column(
                [[sg.Text("Detail", font=("Helvetica", 12, "bold"))], [detail_box]],
                expand_x=True,
                expand_y=True,
            ),
        ],
    ]

    window = sg.Window(
        "Event Viewer",
        layout,
        resizable=True,
        finalize=True,
    )

    # Draw the initial diagram with no highlight.
    _draw_process_diagram(window["-DIAGRAM-"], process_units)

    unit_ids = {unit.get_id() for unit in process_units}

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "Exit"):
            break

        if event == "-TABLE-":
            selected_rows = values.get("-TABLE-", [])
            if not selected_rows:
                continue
            idx = selected_rows[0]
            if idx < 0 or idx >= len(events):
                continue

            selected_event = events[idx]
            window["-DETAIL-"].update(_detail_text(selected_event))

            # Determine which unit to highlight.
            highlight_id: ProcessUnitId | None = None
            if isinstance(selected_event, ConfigurationAppliedEvent):
                uid = selected_event.configuration.simulation_unit_id
                if uid in unit_ids:
                    highlight_id = uid  # type: ignore[assignment]
            elif isinstance(selected_event, StreamPropagatedEvent):
                highlight_id = selected_event.process_unit_id

            _draw_process_diagram(window["-DIAGRAM-"], process_units, highlight_id)

    window.close()
