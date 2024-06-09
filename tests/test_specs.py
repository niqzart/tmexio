from dataclasses import asdict
from typing import Any

import pytest
from pydantic import TypeAdapter
from pydantic_marshals.contains import assert_contains

from tests.example.main import tmex


def generate_ack_schema(ack_body_annotation: Any) -> dict[str, Any]:
    return TypeAdapter(ack_body_annotation).json_schema()


@pytest.mark.parametrize(
    ("event_name", "handler_spec"),
    [
        pytest.param(
            "list-hellos",
            {
                "summary": None,
                "description": None,
                "tags": ["collection sio"],
                "event_body_model": None,
                "ack_code": 200,
                "ack_body_schema": Any,  # list[HelloModel]
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
                "event_body_model": Any,  # {hello: HelloSchema}
                "ack_code": 201,
                "ack_body_schema": Any,  # list[HelloModel]
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
                "event_body_model": None,
                "ack_code": 204,
                "ack_body_schema": {"type": "null"},  # None
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
                "event_body_model": Any,  # {hello: HelloSchema, hello_id: str}
                "ack_code": 200,
                "ack_body_schema": Any,  # HelloModel
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
                "event_body_model": Any,  # {hello_id: str}
                "ack_code": 204,
                "ack_body_schema": {"type": "null"},  # None
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
                "event_body_model": Any,  # {hello_id: str}
                "ack_code": 200,
                "ack_body_schema": Any,  # HelloModel
                "exceptions": [Any, Any],
                # Exceptions:
                #   not_found_exception,
                #   BaseAsyncHandler.zero_arguments_expected_error
            },
            id="retrieve-hello",
        ),
    ],
)
def test_specs(event_name: str, handler_spec: dict[str, Any]) -> None:
    result = tmex.event_handlers.get(event_name)
    assert isinstance(result, tuple)
    assert_contains(asdict(result[1]), handler_spec)
