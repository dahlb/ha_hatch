"""The base entity follows its device in and out of the coordinator."""

from __future__ import annotations

from hatch_rest_api import RestPlus

from custom_components.ha_hatch.binary_sensor import HatchOnlineSensor

from .conftest import FakeCoordinator, build_device

THING = "thing-entity"


def test_entity_is_unavailable_once_its_device_is_gone() -> None:
    """An entity whose device left the account is unavailable instead of raising."""
    device, _ = build_device(RestPlus, THING, "AA:BB:CC:DD:EE:20")
    coordinator = FakeCoordinator([device])
    entity = HatchOnlineSensor(coordinator, THING)  # type: ignore[arg-type]
    assert entity.available is True

    coordinator.rest_devices.clear()

    assert entity.available is False


def test_entity_is_unavailable_when_the_coordinator_update_failed() -> None:
    """A failed coordinator update still makes the entity unavailable."""
    device, _ = build_device(RestPlus, THING, "AA:BB:CC:DD:EE:21")
    coordinator = FakeCoordinator([device])
    entity = HatchOnlineSensor(coordinator, THING)  # type: ignore[arg-type]

    coordinator.last_update_success = False

    assert entity.available is False
