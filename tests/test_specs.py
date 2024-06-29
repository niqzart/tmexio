from dataclasses import asdict
from typing import Any

import pytest
from pydantic_marshals.contains import assert_contains

from tests.example.main import tmex


@pytest.mark.parametrize(
    ("event_name", "handler_spec"),
    [
        pytest.param(
            "list-hellos",
            {
                "summary": None,
                "description": None,
                "tags": ["collection sio"],
                "body_model": None,
                "ack": {
                    "code": 200,
                    "model": Any,  # list[HelloModel]
                },
                "exceptions": [Any],  # BaseAsyncHandler.zero_arguments_expected_error
            },
            id="list_hellos",
        ),
        pytest.param(
            "create-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["collection sio"],
                "body_model": Any,  # {hello: HelloSchema}
                "ack": {
                    "code": 201,
                    "model": Any,  # list[HelloModel]
                },
                "exceptions": [Any],  # BaseAsyncHandler.zero_arguments_expected_error
            },
            id="create-hello",
        ),
        pytest.param(
            "close-hellos",
            {
                "summary": None,
                "description": None,
                "tags": ["collection sio"],
                "body_model": None,
                "ack": {
                    "code": 204,
                    "model": Any,  # None
                },
                "exceptions": [Any],  # BaseAsyncHandler.zero_arguments_expected_error
            },
            id="close-hellos",
        ),
        pytest.param(
            "update-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["entries sio"],
                "body_model": Any,  # {hello: HelloSchema, hello_id: str}
                "ack": {
                    "code": 200,
                    "model": Any,  # HelloModel
                },
                "exceptions": [Any, Any],
                # Exceptions:
                #   not_found_exception,
                #   BaseAsyncHandler.zero_arguments_expected_error
            },
            id="update-hello",
        ),
        pytest.param(
            "delete-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["deleter", "entries sio"],
                "body_model": Any,  # {hello_id: str}
                "ack": {
                    "code": 204,
                    "model": Any,  # None
                },
                "exceptions": [Any],  # BaseAsyncHandler.zero_arguments_expected_error
            },
            id="delete-hello",
        ),
        pytest.param(
            "retrieve-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["entries sio"],
                "body_model": Any,  # {hello_id: str}
                "ack": {
                    "code": 200,
                    "model": Any,  # HelloModel
                },
                "exceptions": [Any, Any],
                # Exceptions:
                #   not_found_exception,
                #   BaseAsyncHandler.zero_arguments_expected_error
            },
            id="retrieve-hello",
        ),
    ],
)
def test_handler_specs(event_name: str, handler_spec: dict[str, Any]) -> None:
    result = tmex.event_handlers.get(event_name)
    assert isinstance(result, tuple)
    assert_contains(asdict(result[1]), handler_spec)


@pytest.mark.parametrize(
    ("event_name", "emitter_spec"),
    [
        pytest.param(
            "new-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["collection sio"],
                "body_model": Any,  # HelloModel
            },
            id="new-hello",
        ),
        pytest.param(
            "update-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["entries sio"],
                "body_model": Any,  # HelloModel
            },
            id="update-hello",
        ),
        pytest.param(
            "delete-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["deleter", "entries sio"],
                "body_model": Any,  # dict[str, Any] / {hello_id: str}
            },
            id="delete-hello",
        ),
    ],
)
def test_emitter_specs(event_name: str, emitter_spec: dict[str, Any]) -> None:
    result = tmex.event_emitters.get(event_name)
    assert result is not None
    assert_contains(asdict(result), emitter_spec)
