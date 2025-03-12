import functools
from flask import request, jsonify
from jsonschema import validate, ValidationError

def validate_json(schema):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            try:
                validate(instance=data, schema=schema)
            except ValidationError as e:
                return {"error": f"JSON validation error: {e.message}"}, 400
            return func(*args, **kwargs)
        return wrapper
    return decorator


API_QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "key": {"type": "string"}
    },
    "required": ["key"],
    "additionalProperties": False
}

API_MODIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "key": {
            "type": "string"
        },
        "operation": {
            "type": "string",
            "enum": ["insert", "delete"]
        },
        "value": {
            "type": "string"
        }
    },
    "required": ["key", "operation"],
    "if": {
        "properties": {
            "operation": {
                "const": "insert"
             }
        }
    },
    "then": {
        "required": ["value"]
    },
    "additionalProperties": False
}

API_OVERLAY_SCHEMA = {
    "type": "object",
    "properties": {},
    "additionalProperties": False
}

API_DEPART_SCHEMA = {
    "type": "object",
    "properties": {},
    "additionalProperties": False
}

SPAWN_SCHEMA = {
    "type": "object",
    "properties": {},
    "additionalProperties": False
}

SPAWN_BOOTSTRAP_SCHEMA = {
    "type": "object",
    "properties": {
        "consistency_model": {
            "type": "string",
            "enum": ["LINEARIZABLE", "EVENTUAL"]
        },
        "replication_factor": {
            "type": "integer",
            "minimum": 1
        }
    },
    "required": ["consistency_model", "replication_factor"],
    "additionalProperties": False
}

LIST_WORKERS_SCHEMA = {
    "type": "object",
    "properties": {},
    "additionalProperties": False
}

KILLALL_SCHEMA = {
    "type": "object",
    "properties": {},
    "additionalProperties": False
}

