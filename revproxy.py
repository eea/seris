# working behind a reverse proxy
# http://flask.pocoo.org/snippets/35/
import os


class ReverseProxied(object):

    def __init__(self, app, config=None):
        self.app = app
        self.config = config

    def __call__(self, environ, start_response):
        script_name = environ.get(
            'HTTP_X_SCRIPT_NAME', os.environ.get(
                'HTTP_X_SCRIPT_NAME', self.config.get(
                    'HTTP_X_SCRIPT_NAME', '')))
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme

        host = environ.get('HTTP_X_FORWARDED_HOST', '')
        if host:
            environ['HTTP_HOST'] = host

        return self.app(environ, start_response)
