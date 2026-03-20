from __future__ import annotations

from collections.abc import Sequence

from nicegui import ui

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

_BOX_W = 100
_BOX_H = 50
_GAP = 40
_MARGIN = 20
_ARROW_LEN = _GAP - 4


def _short_id(uid: object) -> str:
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


def _stream_summary(label: str, stream) -> list[str]:  # noqa: ANN001
    return [
        f"{label}:",
        f"  pressure     = {stream.pressure_bara:.4f} bara",
        f"  temperature  = {stream.temperature_kelvin:.2f} K",
        f"  std rate     = {stream.standard_rate_sm3_per_day:.2f} Sm3/d",
        f"  vol rate     = {stream.volumetric_rate_m3_per_hour:.4f} m3/h",
        f"  density      = {stream.density:.4f} kg/m3",
    ]


def _build_table_rows(events: list[Event]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i, event in enumerate(events):
        if isinstance(event, ConfigurationAppliedEvent):
            cfg = event.configuration
            rows.append(
                {
                    "#": str(i),
                    "Type": "Config",
                    "Unit": _short_id(cfg.simulation_unit_id),
                    "Summary": _config_summary(cfg.value),
                }
            )
        elif isinstance(event, StreamPropagatedEvent):
            rows.append(
                {
                    "#": str(i),
                    "Type": "Stream",
                    "Unit": _short_id(event.process_unit_id),
                    "Summary": f"P: {event.inlet_stream.pressure_bara:.2f} -> {event.outlet_stream.pressure_bara:.2f}",
                }
            )
    return rows


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


def _canvas_size(n_units: int) -> tuple[int, int]:
    width = max(400, _MARGIN * 2 + n_units * _BOX_W + (n_units - 1) * _GAP)
    height = _MARGIN * 2 + _BOX_H
    return width, height


def _build_svg_diagram(
    units: Sequence[ProcessUnit | ProcessSystem],
    highlight_id: ProcessUnitId | None = None,
) -> str:
    canvas_w, canvas_h = _canvas_size(len(units))
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w}" height="{canvas_h}"'
        f' viewBox="0 0 {canvas_w} {canvas_h}" style="background:#ffffff">',
    ]

    x = _MARGIN
    y_mid = _MARGIN + _BOX_H // 2

    for i, unit in enumerate(units):
        is_active = highlight_id is not None and unit.get_id() == highlight_id
        fill = "#4a90d9" if is_active else "#d0d0d0"
        text_color = "#ffffff" if is_active else "#000000"

        rx = x
        ry = y_mid - _BOX_H // 2

        parts.append(
            f'<rect x="{rx}" y="{ry}" width="{_BOX_W}" height="{_BOX_H}" '
            f'fill="{fill}" stroke="#333333" stroke-width="2" rx="4"/>'
        )

        label = _unit_label(unit)
        label_lines = label.split("\n")
        for li, line in enumerate(label_lines):
            ty = y_mid + (li - (len(label_lines) - 1) / 2) * 14
            parts.append(
                f'<text x="{rx + _BOX_W // 2}" y="{ty}" '
                f'text-anchor="middle" dominant-baseline="central" '
                f'fill="{text_color}" font-family="Helvetica, Arial, sans-serif" font-size="11">'
                f"{line}</text>"
            )

        if i < len(units) - 1:
            ax1 = x + _BOX_W + 2
            ax2 = x + _BOX_W + _ARROW_LEN
            parts.append(f'<line x1="{ax1}" y1="{y_mid}" x2="{ax2}" y2="{y_mid}" stroke="#555555" stroke-width="2"/>')
            parts.append(
                f'<polygon points="{ax2},{y_mid} {ax2 - 6},{y_mid - 4} {ax2 - 6},{y_mid + 4}" fill="#555555"/>'
            )

        x += _BOX_W + _GAP

    parts.append("</svg>")
    return "\n".join(parts)


def show_events(
    event_service: EventService,
    process_units: Sequence[ProcessUnit | ProcessSystem],
) -> None:
    events = event_service.get_events()
    table_rows = _build_table_rows(events)
    unit_ids = {unit.get_id() for unit in process_units}

    columns = [
        {"name": "#", "label": "#", "field": "#", "align": "left", "sortable": True},
        {"name": "Type", "label": "Type", "field": "Type", "align": "left", "sortable": True},
        {"name": "Unit", "label": "Unit", "field": "Unit", "align": "left", "sortable": True},
        {"name": "Summary", "label": "Summary", "field": "Summary", "align": "left", "sortable": True},
    ]

    @ui.page("/")
    def index():
        ui.page_title("Event Viewer")

        with ui.column().classes("w-full p-4 gap-4"):
            ui.label("Process System").classes("text-lg font-bold")
            diagram_html = ui.html(_build_svg_diagram(process_units))
            ui.separator()

            with ui.row().classes("w-full gap-4").style("min-height: 400px"):
                with ui.column().classes("flex-1"):
                    ui.label("Events").classes("text-lg font-bold")
                    table = ui.table(
                        columns=columns,
                        rows=table_rows,
                        row_key="#",
                        selection="single",
                    ).classes("w-full")

                ui.separator().props("vertical")

                with ui.column().classes("flex-1"):
                    ui.label("Detail").classes("text-lg font-bold")
                    detail = ui.code("Select an event to see details.").classes("w-full whitespace-pre")

            def on_select(e):
                selected = e.selection
                if not selected:
                    return
                idx = int(selected[0]["#"])
                if idx < 0 or idx >= len(events):
                    return

                selected_event = events[idx]
                detail.set_content(_detail_text(selected_event))

                highlight_id: ProcessUnitId | None = None
                if isinstance(selected_event, ConfigurationAppliedEvent):
                    uid = selected_event.configuration.simulation_unit_id
                    if uid in unit_ids:
                        highlight_id = uid  # type: ignore[assignment]
                elif isinstance(selected_event, StreamPropagatedEvent):
                    highlight_id = selected_event.process_unit_id

                diagram_html.set_content(_build_svg_diagram(process_units, highlight_id))

            table.on_select(on_select)

    ui.run(title="Event Viewer")
