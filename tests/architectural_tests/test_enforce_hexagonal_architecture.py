from pytestarch import Rule


def test_domain_does_not_import_infrastructure(libecalc_architecture):
    rule = (
        Rule()
        .modules_that()
        .are_sub_modules_of("libecalc.process")
        .should_not()
        .import_modules_that()
        .are_sub_modules_of("libecalc.common")
    )

    rule.assert_applies(libecalc_architecture)
