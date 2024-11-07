from libecalc.common.decorators.feature_flags import FeatureToggle


def old_method(test: str) -> str:
    return test + "_old"


def test_feature_toggle_on():
    @FeatureToggle.experimental(True, old_method)
    def new_method(test: str) -> str:
        return test + "_new"

    assert new_method("test") == "test_new"


def test_feature_toggle_off():
    @FeatureToggle.experimental(False, old_method)
    def new_method(test: str) -> str:
        return test + "_new"

    assert new_method("test") == "test_old"
