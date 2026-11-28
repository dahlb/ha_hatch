"""Tests for turning failed Hatch commands into Home Assistant errors."""

from __future__ import annotations

from concurrent.futures import Future
import importlib
import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from awscrt.exceptions import AwsCrtError
from hatch_rest_api import RestIot, shadow_client_subscriber
from homeassistant.exceptions import HomeAssistantError
import pytest

from custom_components.ha_hatch.commands import (
    COMMAND_ERRORS_TRANSLATED,
    hatch_command_errors,
    translate_command_errors,
)
from custom_components.ha_hatch.const import DOMAIN
from custom_components.ha_hatch.hatch_entity import HatchEntity
from custom_components.ha_hatch.light_riot_entity import LightRiotEntity

from .conftest import build_device

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "ha_hatch"
ENTITY_MODULES = (
    "light_rest_entity",
    "light_restoreiot_entity",
    "light_riot_clock_entity",
    "light_riot_entity",
    "media_rest_entity",
    "media_riot_entity",
    "number",
    "restore_entities",
    "scene",
    "select",
    "switch",
    "time",
)
COMMAND_METHODS = frozenset(
    {
        "activate",
        "async_activate",
        "async_media_pause",
        "async_media_play",
        "async_media_stop",
        "async_select_option",
        "async_select_sound_mode",
        "async_set_native_value",
        "async_set_value",
        "async_set_volume_level",
        "async_turn_off",
        "async_turn_on",
        "media_pause",
        "media_play",
        "media_stop",
        "select_option",
        "select_sound_mode",
        "set_native_value",
        "set_value",
        "set_volume_level",
        "turn_off",
        "turn_on",
    }
)
MQTT_TIMEOUT_ERROR = AwsCrtError(5129, "AWS_ERROR_MQTT_TIMEOUT", "Time limit between request")


class FakeEntity:
    """Stand-in entity whose commands fail the way a broken connection does."""

    entity_id = "light.nursery"

    @translate_command_errors
    def turn_on(self, error: Exception | None = None) -> str:
        """Send a command, failing with ``error`` if given.

        Args:
            error: The error to raise, if any.

        Returns:
            A marker showing the command completed.

        Raises:
            Exception: ``error``.
        """
        if error is not None:
            raise error
        return "sent"

    @translate_command_errors
    async def async_turn_on(self, error: Exception | None = None) -> str:
        """Send a command asynchronously, failing with ``error`` if given.

        Args:
            error: The error to raise, if any.

        Returns:
            A marker showing the command completed.

        Raises:
            Exception: ``error``.
        """
        if error is not None:
            raise error
        return "sent"


async def _run(entity: FakeEntity, is_async: bool, error: Exception | None) -> str:
    """Run the fake entity's sync or async command.

    Args:
        entity: The entity.
        is_async: Whether to run the async command.
        error: The error the command raises, if any.

    Returns:
        What the command returned.
    """
    if is_async:
        return await entity.async_turn_on(error)
    return entity.turn_on(error)


@pytest.mark.parametrize("is_async", [False, True])
@pytest.mark.parametrize(
    ("error", "translation_key", "placeholders"),
    [
        (TimeoutError(), "command_timeout", {"target": "light.nursery"}),
        (
            MQTT_TIMEOUT_ERROR,
            "command_failed",
            {"target": "light.nursery", "error": "AWS_ERROR_MQTT_TIMEOUT"},
        ),
    ],
)
async def test_failed_commands_raise_home_assistant_errors(
    is_async: bool,
    error: Exception,
    translation_key: str,
    placeholders: dict[str, str],
) -> None:
    """Timeouts and awscrt failures become HomeAssistantError, keeping the cause."""
    with pytest.raises(HomeAssistantError) as raised:
        await _run(FakeEntity(), is_async, error)

    assert raised.value.translation_domain == DOMAIN
    assert raised.value.translation_key == translation_key
    assert raised.value.translation_placeholders == placeholders
    assert raised.value.__cause__ is error


@pytest.mark.parametrize("is_async", [False, True])
async def test_successful_commands_return_their_result(is_async: bool) -> None:
    """A command that succeeds is unchanged."""
    assert await _run(FakeEntity(), is_async, None) == "sent"


@pytest.mark.parametrize("is_async", [False, True])
async def test_other_errors_are_not_translated(is_async: bool) -> None:
    """Only connection failures are translated; anything else is a real bug."""
    with pytest.raises(ValueError, match="bad value"):
        await _run(FakeEntity(), is_async, ValueError("bad value"))


def test_target_falls_back_to_the_method_name() -> None:
    """Before an entity has an id, the message names the method."""
    entity = FakeEntity()
    entity.entity_id = None  # type: ignore[assignment]

    with pytest.raises(HomeAssistantError) as raised:
        entity.turn_on(TimeoutError())

    assert raised.value.translation_placeholders == {"target": "FakeEntity.turn_on"}


def test_context_manager_translates_failures() -> None:
    """The context manager serves code that is not an entity method."""
    with pytest.raises(HomeAssistantError) as raised, hatch_command_errors("Nursery"):
        raise TimeoutError

    assert raised.value.translation_placeholders == {"target": "Nursery"}


async def test_a_real_mqtt_publish_timeout_becomes_a_home_assistant_error() -> None:
    """The issue's case: a shadow publish never acknowledged within MQTT_TIMEOUT."""
    device, client = build_device(RestIot, "thing-rest", "AA:BB:CC:DD:EE:01")
    # A real future that is never acknowledged; async_command awaits it until
    # MQTT_TIMEOUT, shortened here.
    unacknowledged: Future[None] = Future()
    client.publish_update_shadow = MagicMock(  # type: ignore[method-assign]
        return_value=unacknowledged
    )
    coordinator = MagicMock()
    coordinator.rest_device_by_thing_name.return_value = device
    light = LightRiotEntity(coordinator, "thing-rest")
    light.entity_id = "light.rest_light"

    with (
        patch.object(shadow_client_subscriber, "MQTT_TIMEOUT", 0.01),
        pytest.raises(HomeAssistantError) as raised,
    ):
        await light.async_turn_on()

    assert isinstance(raised.value.__cause__, TimeoutError)
    assert raised.value.translation_placeholders == {"target": "light.rest_light"}


def _entity_classes() -> list[type[Any]]:
    """Return every entity class the integration defines.

    Returns:
        The classes derived from HatchEntity.
    """
    classes: list[type[Any]] = []
    for name in ENTITY_MODULES:
        module = importlib.import_module(f"custom_components.ha_hatch.{name}")
        classes.extend(
            cls
            for _, cls in inspect.getmembers(module, inspect.isclass)
            if cls.__module__ == module.__name__ and issubclass(cls, HatchEntity)
        )
    return classes


def test_every_entity_command_translates_its_errors() -> None:
    """Each command an entity defines is wrapped, so new commands cannot miss it."""
    classes = _entity_classes()
    unwrapped = [
        f"{cls.__name__}.{method}"
        for cls in classes
        for method in COMMAND_METHODS & set(vars(cls))
        if not getattr(vars(cls)[method], COMMAND_ERRORS_TRANSLATED, False)
    ]

    assert len(classes) > 20
    assert unwrapped == []


@pytest.mark.parametrize("path", ["strings.json", "translations/en.json"])
def test_error_messages_are_translated(path: str) -> None:
    """Both error messages exist and use the placeholders the code passes."""
    exceptions = json.loads((INTEGRATION / path).read_text())["exceptions"]

    assert "{target}" in exceptions["command_timeout"]["message"]
    assert "{target}" in exceptions["command_failed"]["message"]
    assert "{error}" in exceptions["command_failed"]["message"]


def test_entity_commands_are_async() -> None:
    """Commands are async and send through async_command, never on an executor thread.

    A sync command method makes Home Assistant run it in its executor, where the
    device's blocking MQTT wait ties up a worker thread.
    """
    sync_commands = [
        f"{cls.__name__}.{method}"
        for cls in _entity_classes()
        for method in sorted(name for name in COMMAND_METHODS if not name.startswith("async_"))
        if method in vars(cls) and not inspect.iscoroutinefunction(vars(cls)[method])
    ]

    assert sync_commands == []
