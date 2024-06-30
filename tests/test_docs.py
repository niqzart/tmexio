from typing import Any

from tests.example.main import tmex
from tmexio.documentation import OpenAPIBuilder

openapi_docs: dict[str, Any] = {
    "openapi": "3.0.1",
    "paths": {
        "/=tmexio-PUB=/list-hellos/": {
            "trace": {
                "operationId": "pub-list-hellos",
                "tags": ["collection sio"],
                "summary": None,
                "description": None,
                "requestBody": None,
                "responses": {
                    "200 ": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "$ref": "#/components/schemas/HelloModel"
                                    },
                                }
                            }
                        },
                    },
                    "422 ": {"description": "Event expects zero arguments"},
                },
            }
        },
        "/=tmexio-PUB=/create-hello/": {
            "trace": {
                "operationId": "pub-create-hello",
                "tags": ["collection sio"],
                "summary": None,
                "description": None,
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/tmexio__handler_builders__create-hello__InputModel"
                            }
                        }
                    },
                },
                "responses": {
                    "201 ": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HelloModel"}
                            }
                        },
                    },
                    "422 ": {"description": "Event expects one argument"},
                    "422  ": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ValidationErrorModel"
                                }
                            }
                        },
                    },
                },
            }
        },
        "/=tmexio-PUB=/close-hellos/": {
            "trace": {
                "operationId": "pub-close-hellos",
                "tags": ["collection sio"],
                "summary": None,
                "description": None,
                "requestBody": None,
                "responses": {
                    "204 ": {
                        "description": "Success",
                        "content": {"application/json": {"schema": {"type": "null"}}},
                    },
                    "422 ": {"description": "Event expects zero arguments"},
                },
            }
        },
        "/=tmexio-PUB=/update-hello/": {
            "trace": {
                "operationId": "pub-update-hello",
                "tags": ["entries sio"],
                "summary": None,
                "description": None,
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/tmexio__handler_builders__update-hello__InputModel"
                            }
                        }
                    },
                },
                "responses": {
                    "200 ": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HelloModel"}
                            }
                        },
                    },
                    "404 ": {"description": "Hello not found"},
                    "422 ": {"description": "Event expects one argument"},
                    "422  ": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ValidationErrorModel"
                                }
                            }
                        },
                    },
                },
            }
        },
        "/=tmexio-PUB=/delete-hello/": {
            "trace": {
                "operationId": "pub-delete-hello",
                "tags": ["deleter", "entries sio"],
                "summary": None,
                "description": None,
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/tmexio__handler_builders__delete-hello__InputModel"
                            }
                        }
                    },
                },
                "responses": {
                    "204 ": {
                        "description": "Success",
                        "content": {"application/json": {"schema": {"type": "null"}}},
                    },
                    "422 ": {"description": "Event expects one argument"},
                    "422  ": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ValidationErrorModel"
                                }
                            }
                        },
                    },
                },
            }
        },
        "/=tmexio-PUB=/retrieve-hello/": {
            "trace": {
                "operationId": "pub-retrieve-hello",
                "tags": ["entries sio"],
                "summary": None,
                "description": None,
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/tmexio__handler_builders__retrieve-hello__InputModel"
                            }
                        }
                    },
                },
                "responses": {
                    "200 ": {
                        "description": "Success",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HelloModel"}
                            }
                        },
                    },
                    "404 ": {"description": "Hello not found"},
                    "422 ": {"description": "Event expects one argument"},
                    "422  ": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ValidationErrorModel"
                                }
                            }
                        },
                    },
                },
            }
        },
        "/=tmexio-PUB=/*/": {
            "trace": {
                "operationId": "pub-*",
                "tags": [],
                "summary": None,
                "description": None,
                "requestBody": None,
                "responses": {
                    "404 ": {
                        "description": "Success",
                        "content": {"application/json": {"schema": {"type": "string"}}},
                    },
                    "422 ": {"description": "Event expects zero arguments"},
                },
            }
        },
        "/=tmexio-PUB=/connect/": {
            "trace": {
                "operationId": "pub-connect",
                "tags": [],
                "summary": None,
                "description": None,
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/tmexio__handler_builders__connect__InputModel"
                            }
                        }
                    },
                },
                "responses": {
                    "401 ": {"description": "Authorization missing or invalid"},
                    "422 ": {"description": "Event expects one argument"},
                    "422  ": {
                        "description": "Validation Error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ValidationErrorModel"
                                }
                            }
                        },
                    },
                },
            }
        },
        "/=tmexio-PUB=/disconnect/": {
            "trace": {
                "operationId": "pub-disconnect",
                "tags": [],
                "summary": None,
                "description": None,
                "requestBody": None,
                "responses": {},
            }
        },
        "/=tmexio-SUB=/new-hello/": {
            "head": {
                "operationId": "sub-new-hello",
                "tags": ["collection sio"],
                "summary": None,
                "description": None,
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/HelloModel"}
                        }
                    },
                },
            }
        },
        "/=tmexio-SUB=/update-hello/": {
            "head": {
                "operationId": "sub-update-hello",
                "tags": ["entries sio"],
                "summary": None,
                "description": None,
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/HelloModel"}
                        }
                    },
                },
            }
        },
        "/=tmexio-SUB=/delete-hello/": {
            "head": {
                "operationId": "sub-delete-hello",
                "tags": ["deleter", "entries sio"],
                "summary": None,
                "description": None,
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"type": "object"}}},
                },
            }
        },
    },
    "components": {
        "schemas": {
            "ErrorDetailsModel": {
                "properties": {
                    "type": {"title": "Type", "type": "string"},
                    "loc": {
                        "items": {"anyOf": [{"type": "integer"}, {"type": "string"}]},
                        "title": "Loc",
                        "type": "array",
                    },
                    "msg": {"title": "Msg", "type": "string"},
                },
                "required": ["type", "loc", "msg"],
                "title": "ErrorDetailsModel",
                "type": "object",
            },
            "HelloModel": {
                "properties": {
                    "text": {"title": "Text", "type": "string"},
                    "created": {
                        "format": "date-time",
                        "title": "Created",
                        "type": "string",
                    },
                    "id": {"title": "Id", "type": "string"},
                },
                "required": ["text"],
                "title": "HelloModel",
                "type": "object",
            },
            "HelloSchema": {
                "properties": {
                    "text": {"title": "Text", "type": "string"},
                    "created": {
                        "format": "date-time",
                        "title": "Created",
                        "type": "string",
                    },
                },
                "required": ["text"],
                "title": "HelloSchema",
                "type": "object",
            },
            "ValidationErrorModel": {
                "properties": {
                    "detail": {
                        "items": {"$ref": "#/components/schemas/ErrorDetailsModel"},
                        "title": "Detail",
                        "type": "array",
                    }
                },
                "required": ["detail"],
                "title": "ValidationErrorModel",
                "type": "object",
            },
            "tmexio__handler_builders__connect__InputModel": {
                "properties": {"token": {"title": "Token", "type": "string"}},
                "required": ["token"],
                "title": "connect.InputModel",
                "type": "object",
            },
            "tmexio__handler_builders__create-hello__InputModel": {
                "properties": {"hello": {"$ref": "#/components/schemas/HelloSchema"}},
                "required": ["hello"],
                "title": "create-hello.InputModel",
                "type": "object",
            },
            "tmexio__handler_builders__delete-hello__InputModel": {
                "properties": {"hello_id": {"title": "Hello Id", "type": "string"}},
                "required": ["hello_id"],
                "title": "delete-hello.InputModel",
                "type": "object",
            },
            "tmexio__handler_builders__retrieve-hello__InputModel": {
                "properties": {"hello_id": {"title": "Hello Id", "type": "string"}},
                "required": ["hello_id"],
                "title": "retrieve-hello.InputModel",
                "type": "object",
            },
            "tmexio__handler_builders__update-hello__InputModel": {
                "properties": {
                    "hello_id": {"title": "Hello Id", "type": "string"},
                    "hello": {"$ref": "#/components/schemas/HelloSchema"},
                },
                "required": ["hello_id", "hello"],
                "title": "update-hello.InputModel",
                "type": "object",
            },
        }
    },
}


def test_openapi() -> None:
    builder = OpenAPIBuilder(tmex)
    # TODO use assert_contains after https://github.com/niqzart/pydantic-marshals/issues/29
    assert builder.build_documentation() == openapi_docs
