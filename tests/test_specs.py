from dataclasses import asdict
from typing import Any

import pytest
from pydantic import BaseModel, TypeAdapter
from pydantic_marshals.contains import assert_contains

from tests.example.main import tmex


@pytest.mark.parametrize(
    ("event_name", "handler_spec", "expected_body_model", "expected_ack_model"),
    [
        pytest.param(
            "list-hellos",
            {
                "summary": None,
                "description": None,
                "tags": ["collection sio"],
                "body_model": None,
                "ack": {"code": 200},
                "exceptions": [Any],  # BaseAsyncHandler.zero_arguments_expected_error
            },
            None,
            "list[HelloModel]",
            id="list_hellos",
        ),
        pytest.param(
            "create-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["collection sio"],
                "ack": {"code": 201},
                "exceptions": [Any],  # BaseAsyncHandler.zero_arguments_expected_error
            },
            {"hello_data": "HelloSchema"},
            "HelloModel",
            id="create-hello",
        ),
        pytest.param(
            "close-hellos",
            {
                "summary": None,
                "description": None,
                "tags": ["collection sio"],
                "body_model": None,
                "ack": {"code": 204},
                "exceptions": [Any],  # BaseAsyncHandler.zero_arguments_expected_error
            },
            None,
            "none",
            id="close-hellos",
        ),
        pytest.param(
            "update-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["entries sio"],
                "ack": {"code": 200},
                "exceptions": [Any, Any],
                # Exceptions:
                #   not_found_exception,
                #   BaseAsyncHandler.zero_arguments_expected_error
            },
            {"hello_data": "HelloSchema", "hello_id": "str"},
            "HelloModel",
            id="update-hello",
        ),
        pytest.param(
            "delete-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["deleter", "entries sio"],
                "ack": {"code": 204},
                "exceptions": [Any],  # BaseAsyncHandler.zero_arguments_expected_error
            },
            {"hello_id": "str"},
            "none",
            id="delete-hello",
        ),
        pytest.param(
            "retrieve-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["entries sio"],
                "ack": {"code": 200},
                "exceptions": [Any, Any],
                # Exceptions:
                #   not_found_exception,
                #   BaseAsyncHandler.zero_arguments_expected_error
            },
            {"hello_id": "str"},
            "HelloModel",
            id="retrieve-hello",
        ),
    ],
)
def test_handler_specs(
    event_name: str,
    handler_spec: dict[str, Any],
    expected_body_model: dict[str, str] | None,
    expected_ack_model: str,
) -> None:
    result = tmex.event_handlers.get(event_name)
    assert isinstance(result, tuple)
    result_dict = asdict(result[1])

    assert_contains(result_dict, handler_spec)

    real_body_model = result_dict.get("body_model")
    if expected_body_model is None:
        assert real_body_model is None
    else:
        assert isinstance(real_body_model, type)
        assert issubclass(real_body_model, BaseModel)
        assert_contains(
            {
                k: str(list(v.__repr_args__())[0][1])
                for k, v in real_body_model.model_fields.items()
            },
            expected_body_model,
        )

    real_ack_model = result_dict["ack"].get("model")
    assert isinstance(real_ack_model, TypeAdapter)
    assert real_ack_model.validator.title == expected_ack_model


@pytest.mark.parametrize(
    ("event_name", "emitter_spec", "expected_body_model"),
    [
        pytest.param(
            "new-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["collection sio"],
            },
            "HelloModel",
            id="new-hello",
        ),
        pytest.param(
            "update-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["entries sio"],
            },
            "HelloModel",
            id="update-hello",
        ),
        pytest.param(
            "delete-hello",
            {
                "summary": None,
                "description": None,
                "tags": ["deleter", "entries sio"],
            },
            "dict[str,any]",  # {hello_id: str}
            id="delete-hello",
        ),
    ],
)
def test_emitter_specs(
    event_name: str, emitter_spec: dict[str, Any], expected_body_model: str
) -> None:
    result = tmex.event_emitters.get(event_name)
    assert result is not None
    result_dict = asdict(result)

    assert_contains(result_dict, emitter_spec)

    real_body_model = result_dict.get("body_model")
    assert isinstance(real_body_model, TypeAdapter)
    assert real_body_model.validator.title == expected_body_model
