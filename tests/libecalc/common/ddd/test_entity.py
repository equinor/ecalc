"""
Test and demonstrate "DDD" tactical patterns

TODO: Should we test type-inference for typechecker with pytest-pyright plugin?
https://pytest-pyright.readthedocs.io/en/latest/

ie, that we understand and use type-inference correctly

Part of our code assumes that we cannot make mistakes such
as assigning wrong ID etc
"""

from typing import Final, NewType
from uuid import UUID

import pytest

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator

DummyId = NewType("DummyId", UUID)


class DummyEntity(Entity[DummyId]):
    """
    Minimal dummy entity that demonstrates the DDD Entity contract,
    and how we intend that classes should implement it
    """

    def __init__(self, dummy_id: DummyId | None = None) -> None:
        self._id: Final[DummyId] = dummy_id or DummyEntity._create_id()

    def get_id(self) -> DummyId:
        return self._id

    @classmethod
    def _create_id(cls) -> DummyId:
        return DummyId(ecalc_id_generator())


TommyId = NewType("TommyId", UUID)


class TommyEntity(Entity[TommyId]):
    def __init__(self, tommy_id: TommyId | None = None) -> None:
        self._id: Final[TommyId] = tommy_id or TommyEntity._create_id()

    def get_id(self) -> TommyId:
        return self._id

    @classmethod
    def _create_id(cls) -> TommyId:
        return TommyId(ecalc_id_generator())


def test_id_is_uuid():
    entity = DummyEntity()
    assert isinstance(entity.get_id(), UUID)


def test_two_instances_have_different_ids():
    a = DummyEntity()
    b = DummyEntity()
    assert a.get_id() != b.get_id()


def test_explicit_id_is_preserved():
    explicit_id = DummyId(ecalc_id_generator())
    entity = DummyEntity(dummy_id=explicit_id)
    assert entity.get_id() == explicit_id


def test_same_entity_is_equal():
    entity = DummyEntity()
    assert entity == entity


def test_same_id_is_equal():
    shared_id = DummyId(ecalc_id_generator())
    assert DummyEntity(shared_id) == DummyEntity(shared_id)


def test_different_ids_are_not_equal():
    assert DummyEntity() != DummyEntity()


def test_different_entity_types_with_same_uuid_are_not_equal():
    shared_uuid = ecalc_id_generator()
    assert DummyEntity(DummyId(shared_uuid)) != TommyEntity(TommyId(shared_uuid))


def test_comparing_with_none_returns_false():
    entity = DummyEntity()
    assert (entity == None) is False  # noqa: E711  (intentional None comparison)


def test_comparing_with_non_entity_raises_type_error():
    entity = DummyEntity()
    with pytest.raises(TypeError, match="Cannot compare Entity with"):
        assert entity == "not-an-entity"  # noqa: B015


def test_entity_usable_in_set():
    # Same type and id, is the same, and will yield 1 entity in a set
    shared_id = DummyId(ecalc_id_generator())
    a = DummyEntity(shared_id)
    b = DummyEntity(shared_id)
    assert len({a, b}) == 1


def test_entities_with_different_ids_distinct_in_set():
    assert len({DummyEntity(), DummyEntity()}) == 2
