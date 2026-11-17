from libecalc.common.errors.docs_reference import DocsPage, DocsReference


def test_render_gives_message_and_url_below_the_base_url():
    reference = DocsReference(page=DocsPage.MIGRATE_COMPRESSOR_SAMPLED, message="Convert the file")

    assert reference.render("https://equinor.github.io/ecalc/v15.7/") == (
        "Convert the file: https://equinor.github.io/ecalc/v15.7/docs/about/nextgen/migrate-compressor-sampled"
    )
