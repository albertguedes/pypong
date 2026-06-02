import os
import uuid
from functools import wraps
from flask import request, g
from flask.wrappers import Response
import json


TRACE_HEADER = "X-Request-ID"


def get_request_id():
    return request.headers.get(TRACE_HEADER, str(uuid.uuid4()))


def error_response(code: str, message: str, details: dict = None, status: int = 400):
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        }
    }
    return Response(json.dumps(payload), status=status, mimetype="application/json")


def json_error(status: int, code: str, message: str, details: dict = None):
    return error_response(code, message, details, status)


class TraceMiddleware:
    def __init__(self, app=None):
        self.app = app

    def __call__(self, environ, start_response):
        request_id = environ.get("HTTP_X_REQUEST_ID", str(uuid.uuid4()))
        environ["X-Request-ID"] = request_id
        environ["pypong.request_id"] = request_id
        return self.app(environ, start_response)

    def init_app(self, app):
        self.app = app.wsgi_app
        app.wsgi_app = self

        @app.before_request
        def before():
            g.request_id = get_request_id()

        @app.after_request
        def after(response):
            response.headers[TRACE_HEADER] = g.get("request_id", "")
            return response
