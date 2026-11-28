"""Turn failed Hatch device commands into Home Assistant errors.

Every command goes through ``hatch_rest_api``'s MQTT shadow update, which waits
for the publish to be acknowledged. When the connection drops, that wait ends
in a raw ``TimeoutError``, or awscrt reports the failure as an ``AwsCrtError``.
Home Assistant treats any exception other than ``HomeAssistantError`` as a bug,
so an automation's ``continue_on_error: true`` would not apply and the run
would stop. Commands are therefore wrapped so those failures surface as
``HomeAssistantError``, with the original exception kept as the cause.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine, Iterator
from contextlib import contextmanager
from functools import wraps
from inspect import iscoroutinefunction
import logging
from typing import Any, Final

from awscrt.exceptions import AwsCrtError
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

COMMAND_ERRORS: Final = (TimeoutError, AwsCrtError)
COMMAND_ERRORS_TRANSLATED: Final = "_hatch_command_errors_translated"


@contextmanager
def hatch_command_errors(target: str) -> Iterator[None]:
    """Raise a failed Hatch command as a ``HomeAssistantError``.

    Args:
        target: What the command was for, such as an entity id, for the message.

    Yields:
        Nothing; the command runs inside the ``with`` block.

    Raises:
        HomeAssistantError: The command timed out or the MQTT connection failed.
    """
    try:
        yield
    except TimeoutError as error:
        _LOGGER.debug("Hatch command for %s timed out", target, exc_info=True)
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="command_timeout",
            translation_placeholders={"target": target},
        ) from error
    except AwsCrtError as error:
        _LOGGER.debug("Hatch command for %s failed", target, exc_info=True)
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="command_failed",
            translation_placeholders={"target": target, "error": error.name},
        ) from error


def _command_target(args: tuple[Any, ...], function: Callable[..., Any]) -> str:
    """Return what a command is for: its entity's id, else the method's name.

    Args:
        args: The command's positional arguments; the first is the entity.
        function: The command method.

    Returns:
        The entity id, or the method's qualified name before the entity has one.
    """
    entity_id = getattr(args[0], "entity_id", None) if args else None
    return entity_id if isinstance(entity_id, str) else function.__qualname__


def translate_command_errors[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    """Wrap an entity command so failed Hatch commands raise ``HomeAssistantError``.

    Works on both plain and ``async`` methods.

    Args:
        function: The command method.

    Returns:
        The wrapped method.
    """
    if iscoroutinefunction(function):
        coroutine_function: Callable[P, Coroutine[Any, Any, Any]] = function

        @wraps(function)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            """Run the async command, translating its failures.

            Args:
                *args: The command's positional arguments.
                **kwargs: The command's keyword arguments.

            Returns:
                What the command returns.
            """
            with hatch_command_errors(_command_target(args, function)):
                return await coroutine_function(*args, **kwargs)

        setattr(async_wrapper, COMMAND_ERRORS_TRANSLATED, True)
        return async_wrapper  # type: ignore[return-value]

    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        """Run the command, translating its failures.

        Args:
            *args: The command's positional arguments.
            **kwargs: The command's keyword arguments.

        Returns:
            What the command returns.
        """
        with hatch_command_errors(_command_target(args, function)):
            return function(*args, **kwargs)

    setattr(wrapper, COMMAND_ERRORS_TRANSLATED, True)
    return wrapper
