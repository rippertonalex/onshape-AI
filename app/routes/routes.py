from werkzeug.middleware.dispatcher import DispatcherMiddleware

from app.middlewares.logger_middleware import log_request_info, log_response_info
from app.routes.chat_routes import chat_routes


from app.utils.messages import Error
from app.utils.response import Response


blueprints = {"/chat": chat_routes}


def stop(env, resp):
    resp("200 OK", [("Content-Type", "text/plain")])
    return [b"Dentops API. Basepath /v1/"]


def init_routes(app):
    app.wsgi_app = DispatcherMiddleware(stop, {"/v1": app.wsgi_app})

    app.before_request(log_request_info)
    app.after_request(log_response_info)

    for path in blueprints:
        app.register_blueprint(blueprints[path], url_prefix=path)

    @app.get("/")
    def index():
        return Response(
            {"api_version": "v0.1", "api_description": "Dentops API"},
            Response.HTTP_SUCCESS,
        ).build()

    @app.errorhandler(404)
    def not_found(error):
        return Response.make(Error.NOT_FOUND, Response.HTTP_NOT_FOUND)

    @app.errorhandler(401)
    def unauthorized(error):
        return Response.make(Error.UNAUTHORIZED, Response.HTTP_UNAUTHORIZED)

    @app.errorhandler(500)
    def internal_server_error(error):
        return Response.make(Error.INTERNAL_SERVER_ERROR, Response.HTTP_ERROR)

    @app.errorhandler(400)
    def bad_request(error):
        return Response.make(Error.BAD_REQUEST, Response.HTTP_BAD_REQUEST)
