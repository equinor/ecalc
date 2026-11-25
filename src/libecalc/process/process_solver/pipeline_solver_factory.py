from libecalc.process.process_solver.multi_pressure_solver import MultiPressureSolver
from libecalc.process.process_solver.pipeline_section import Pipeline
from libecalc.process.process_solver.pipeline_section_solver import PipelineSectionSolver
from libecalc.process.process_solver.pipeline_solver import PipelineSolver


def create_pipeline_solver(pipeline: Pipeline) -> PipelineSolver:
    pipeline_sections = pipeline.get_process_pipeline_sections()
    if len(pipeline_sections) == 1:
        return PipelineSectionSolver(pipeline_section=pipeline_sections[0])
    return MultiPressureSolver(pipeline=pipeline)
