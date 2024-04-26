from tmexio.types import DataType


class EventException(Exception):
    def __init__(self, *ack_data: DataType) -> None:
        self.ack_data = ack_data
