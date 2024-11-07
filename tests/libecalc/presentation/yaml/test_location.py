from datetime import date

from libecalc.presentation.yaml.validation_errors import Location


class TestLocation:
    def test_single_key(self):
        location = Location(keys=["INSTALLATION"])
        assert location.as_dot_separated() == "INSTALLATION"

    def test_keys_with_int(self):
        location = Location(keys=["INSTALLATION", 1])
        assert location.as_dot_separated() == "INSTALLATION[1]"

    def test_keys_with_date(self):
        location = Location.from_pydantic_loc(("INSTALLATION", 1, "HCEXPORT", "datetime.date(2019, 1, 1)"))
        assert location.as_dot_separated() == "INSTALLATION[1].HCEXPORT.2019-01-01"


class TestLocationParseDate:
    def test_parse_key_date(self):
        expected_date = date(2018, 1, 1)
        date_repr = repr(expected_date)
        d = Location._parse_key(date_repr)
        assert d == expected_date
