import pytest
from pytestarch import Rule


@pytest.mark.arch
def test_common_to_not_import_process(libecalc_architecture):
    rule = (
        Rule()
        .modules_that()
        .are_named("libecalc.common")
        .should_only()
        .import_modules_that()
        .are_named(
            ["libecalc.common", "libecalc.expression"]
        )  # TODO: What to do with expression? Is it a part of ecalc_model "domain" only?
    )

    rule.assert_applies(libecalc_architecture)


@pytest.mark.arch
def test_process_to_import_process_or_common_only(libecalc_architecture):
    allowed_process_dependencies = [
        "libecalc.common",
        "libecalc.process",
        "libecalc.domain",  # TODO due to train utils and charts
    ]
    rule = (
        Rule()
        .modules_that()
        .are_named("libecalc.process")
        .should_only()
        .import_modules_that()
        .are_named(allowed_process_dependencies)
    )
    rule.assert_applies(libecalc_architecture)
