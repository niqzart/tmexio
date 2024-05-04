from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Annotated, ClassVar
from uuid import uuid4

from pydantic import BaseModel, Field


class HelloSchema(BaseModel):
    text: str
    created: Annotated[datetime, Field(default_factory=datetime.now)]


# Service, repository, model, driver and database in the same class because we can
class HelloModel(HelloSchema):
    collection: ClassVar[dict[str, HelloModel]] = {}

    id: Annotated[str, Field(default_factory=lambda: uuid4().hex)]  # noqa: VNE003

    @classmethod
    def find_first_by_id(cls, entry_id: str) -> HelloModel | None:
        return cls.collection.get(entry_id)

    @classmethod
    def find_all(cls) -> Iterable[HelloModel]:
        yield from cls.collection.values()

    @classmethod
    def create(cls, data: HelloSchema) -> HelloModel:
        entry = cls.model_validate(data, from_attributes=True)
        entry.save()
        return entry

    def update(self, data: HelloSchema) -> None:
        for key, value in data.model_dump().items():
            setattr(self, key, value)
        self.save()

    def save(self) -> None:
        self.collection[self.id] = self

    def delete(self) -> None:
        self.collection.pop(self.id)
