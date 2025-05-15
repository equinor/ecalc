import uuid

from libecalc.domain.infrastructure.path_id import PathID


def test_unique_name_path_id():
    path_id = PathID("some_name")
    assert path_id.get_name() == "some_name"
    assert isinstance(path_id.get_model_unique_id(), uuid.UUID)
    assert path_id.get_parent() is None
    assert path_id.get_unique_tuple_str() == ("some_name",)


def test_path_id_is_reproducible():
    parent_id = PathID("parent")

    child_id = PathID("child", parent=parent_id)

    assert child_id.get_parent() == parent_id

    second_instance_child_id = PathID("child", parent_id)

    assert second_instance_child_id.get_model_unique_id() == child_id.get_model_unique_id()
