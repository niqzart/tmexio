from collections.abc import Iterable

from pydantic import BaseModel, TypeAdapter
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode, JsonSchemaValue
from pydantic_core import CoreSchema

from tmexio.main import TMEXIO
from tmexio.types import ModelType


class ErrorDetailsModel(BaseModel):
    type: str  # noqa: VNE003
    loc: tuple[int | str, ...]
    msg: str


class ValidationErrorModel(BaseModel):
    detail: list[ErrorDetailsModel]


class DocumentationBuilder:
    def __init__(self, tmexio: TMEXIO, model_prefix: str = "") -> None:
        self.tmexio = tmexio
        self.model_prefix = model_prefix

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

    def build_json_schema(self, ref_template: str) -> tuple[
        dict[tuple[ModelType, JsonSchemaMode], JsonSchemaValue],
        dict[str, JsonSchemaValue],
    ]:
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
        return json_schemas_map, {
            f"{self.model_prefix}{key}": value for key, value in json_schema.items()
        }
