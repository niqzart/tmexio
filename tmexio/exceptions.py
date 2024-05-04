from tmexio.types import DataType


class EventException(Exception):
    def __init__(self, code: int, ack_body: DataType) -> None:
        self.code = code
        self.ack_body = ack_body
