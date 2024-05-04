from tmexio import EventException

ROOM_NAME = "helloers"

authorization_exception = EventException(401, "Authorization missing or invalid")
parsing_exception = EventException(422, "Parsing Exception")
not_found_exception = EventException(404, "Hello not found")
