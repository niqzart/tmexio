from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, TypeAdapter
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode, JsonSchemaValue
from pydantic_core import CoreSchema

from tmexio.main import TMEXIO
from tmexio.specs import EmitterSpec, HandlerSpec
from tmexio.types import ModelType


class ErrorDetailsModel(BaseModel):
    type: str  # noqa: VNE003
    loc: tuple[int | str, ...]
    msg: str


class ValidationErrorModel(BaseModel):
    detail: list[ErrorDetailsModel]


JSONSchemasMapType = dict[tuple[ModelType, JsonSchemaMode], JsonSchemaValue]


class DocumentationBuilder:
    def __init__(self, tmexio: TMEXIO, model_prefix: str = "") -> None:
        self.tmexio = tmexio
        self.model_prefix = model_prefix

        self._json_schemas_map: JSONSchemasMapType | None = None

    @property
    def json_schemas_map(self) -> JSONSchemasMapType:  # noqa: FNE002 (map is a noun)
        if self._json_schemas_map is None:
            raise ValueError("json_schemas_map not initialized yet")
        return self._json_schemas_map

    def collect_models(self) -> Iterable[tuple[ModelType, JsonSchemaMode]]:
        for _, handler_spec in self.tmexio.event_handlers.values():
            if handler_spec.body_model is not None:
                yield handler_spec.body_model, "validation"
            if handler_spec.ack is not None and handler_spec.ack.model is not None:
                yield handler_spec.ack.model, "serialization"

        for emitter_spec in self.tmexio.event_emitters.values():
            yield emitter_spec.body_model, "serialization"

        yield ValidationErrorModel, "serialization"

    def model_to_core_schema(self, model: ModelType) -> CoreSchema:
        if isinstance(model, TypeAdapter):
            return model.core_schema
        return model.__pydantic_core_schema__

    def build_json_schema(self, ref_template: str) -> dict[str, JsonSchemaValue]:
        generator = GenerateJsonSchema(
            ref_template=ref_template.replace(
                "{model}", f"{self.model_prefix}{{model}}"
            )
        )
        json_schemas_map, json_schema = generator.generate_definitions(
            [
                (model, mode, self.model_to_core_schema(model))
                for model, mode in self.collect_models()
            ]
        )
        self._json_schemas_map = json_schemas_map
        return {
            f"{self.model_prefix}{key}": value for key, value in json_schema.items()
        }

    def build_documentation(self) -> dict[str, Any]:
        raise NotImplementedError


class OpenAPIBuilder(DocumentationBuilder):
    def build_handler_request_body(self, spec: HandlerSpec) -> dict[str, Any] | None:
        if spec.body_model is None:
            return None
        return {
            "required": True,
            "content": {
                "application/json": {
                    "schema": self.json_schemas_map[(spec.body_model, "validation")]
                }
            },
        }

    def build_response_content(self, model: ModelType | None) -> dict[str, Any] | None:
        if model is None:
            return None
        return {
            "application/json": {
                "schema": self.json_schemas_map[(model, "serialization")]
            }
        }

    def collect_handler_responses(
        self, spec: HandlerSpec
    ) -> Iterable[tuple[int, dict[str, Any]]]:
        if spec.ack is not None:
            yield spec.ack.code, {
                "description": "Success",
                "content": self.build_response_content(spec.ack.model),
            }

        for exception in spec.exceptions:
            if not isinstance(exception.ack_body, str):
                raise NotImplementedError()

            yield exception.code, {"description": exception.ack_body}

        if spec.body_model is not None:
            yield 422, {
                "description": "Validation Error",
                "content": self.build_response_content(ValidationErrorModel),
            }

    def build_handler_responses(self, spec: HandlerSpec) -> dict[str, dict[str, Any]]:
        responses: dict[int, list[dict[str, Any]]] = defaultdict(list)

        for code, response in self.collect_handler_responses(spec):
            responses[code].append(response)

        return {
            str(code) + " " * i: response  # noqa: WPS441 (linter bug)
            for code, rs in responses.items()
            for i, response in enumerate(rs, start=1)
        }

    def build_handler_operation(
        self, event_name: str, spec: HandlerSpec
    ) -> dict[str, Any]:
        return {
            "operationId": f"pub-{event_name}",
            "tags": spec.tags,
            "summary": spec.summary,
            "description": spec.description,
            "requestBody": self.build_handler_request_body(spec),
            "responses": self.build_handler_responses(spec),
        }

    def build_emitter_request_body(self, spec: EmitterSpec) -> dict[str, Any]:
        return {
            "required": True,
            "content": {
                "application/json": {
                    "schema": self.json_schemas_map[(spec.body_model, "serialization")]
                }
            },
        }

    def build_emitter_operation(
        self, event_name: str, spec: EmitterSpec
    ) -> dict[str, Any]:
        return {
            "operationId": f"sub-{event_name}",
            "tags": spec.tags,
            "summary": spec.summary,
            "description": spec.description,
            "requestBody": self.build_emitter_request_body(spec),
        }

    def collect_paths(self) -> Iterable[tuple[str, dict[str, Any]]]:
        for event_name, (_, handler_spec) in self.tmexio.event_handlers.items():
            yield f"/=tmexio-PUB=/{event_name}/", {
                "trace": self.build_handler_operation(event_name, handler_spec)
            }

        for event_name, emitter_spec in self.tmexio.event_emitters.items():
            yield f"/=tmexio-SUB=/{event_name}/", {
                "head": self.build_emitter_operation(event_name, emitter_spec)
            }

    def build_documentation(self) -> dict[str, Any]:
        json_schema = self.build_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        return {
            "openapi": "3.0.1",
            "paths": dict(self.collect_paths()),
            "components": {"schemas": json_schema},
        }
