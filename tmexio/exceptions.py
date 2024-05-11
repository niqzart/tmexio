from __future__ import annotations

from typing import cast

from pydantic import ValidationError

from tmexio.types import DataType


class EventException(Exception):
    def __init__(self, code: int, ack_body: DataType) -> None:
        self.code = code
        self.ack_body = ack_body


class EventBodyException(EventException):
    def __init__(self, validation_error: ValidationError) -> None:
        super().__init__(code=422, ack_body=cast(DataType, validation_error.errors()))


class UndocumentedExceptionWarning(RuntimeWarning):
    def __init__(self, exception: EventException) -> None:
        super().__init__(f"Exception {exception} is not documented, but was raised")
