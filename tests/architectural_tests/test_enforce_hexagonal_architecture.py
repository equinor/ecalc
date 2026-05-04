from pytestarch import Rule


def test_common_to_not_import_process(libecalc_architecture):
    rule = (
        Rule()
        .modules_that()
        .are_sub_modules_of("libecalc.common")
        .should_not()
        .import_modules_that()
        .are_sub_modules_of("libecalc.process")
    )

    rule.assert_applies(libecalc_architecture)


def test_process_to_import_process_or_common_only(libecalc_architecture):
    # TODO: libecalc.domain due to train utils
    # TODO: libecalc.domain due to charts
    for forbidden_process_dep in [
        "libecalc.application",
        "libecalc.core",
        "libecalc.dto",
        "libecalc.ecalc_model",
        "libecalc.examples",
        "libecalc.expression",
        "libecalc.fixtures",
        "libecalc.infrastructure",
        "libecalc.presentation",
        "libecalc.testing",
    ]:
        rule = (
            Rule()
            .modules_that()
            .are_sub_modules_of("libecalc.process")
            .should_not()
            .import_modules_that()
            .are_sub_modules_of(forbidden_process_dep)
        )
        rule.assert_applies(libecalc_architecture)
