from libecalc.dto.utils.string_utils import generate_id, get_duplicates


class TestGetDuplicates:
    def test_no_duplicates(self):
        assert get_duplicates(["name1", "name2", "name3"]) == set()

    def test_duplicates(self):
        assert get_duplicates(["name1", "name2", "name1"]) == {"name1"}


class TestGenerateId:
    def test_single_string(self):
        assert isinstance(generate_id("some_name"), str)

    def test_multiple_strings(self):
        assert isinstance(generate_id("some_prefix", "some_type", "some_name"), str)
