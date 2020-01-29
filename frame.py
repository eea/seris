import flask
import jinja2
import requests


def _process_frame_html(html):
    substitutions = [
        ("{%", "{{ '{%' }}"),
        ("%}", "{{ '%}' }}"),
        ("{{", "{{ '{{' }}"),
        ("}}", "{{ '}}' }}"),
        ("<!-- block_messages -->",
            "{% block action_buttons %}{% endblock %}"
            "{% block messages %}{% endblock %}"),
        ("<!-- block_content -->",
            "{% block seris_content %}{% endblock %}"),
        ("<!-- block_head -->",
            "{% block head %}{% endblock %}"),
    ]

    html = html.strip()
    for sub_a, sub_b in substitutions:
        html = html.replace(sub_a, sub_b)
    return html


class FrameTemplateLoader(jinja2.BaseLoader):

    def get_source(self, environment, template):
        frame_response = getattr(flask.g, 'frame_response', None)

        if template != 'frame.html' or frame_response is None:
            raise jinja2.TemplateNotFound(template)

        path = ':frame-templates:%s' % template
        source = _process_frame_html(flask.g.frame_response['frame_html'])
        return source, path, lambda: False


def get_frame_before_request():
    app = flask.current_app
    url = app.config['FRAME_URL']
    if url is None:
        if not app.debug:
            raise Exception('No FRAME_URL defined.')
        return
    forwarded_cookies = {}
    for name in app.config.get('FRAME_COOKIES', []):
        if name in flask.request.cookies:
            forwarded_cookies[name] = flask.request.cookies[name]
    response = requests.get(url, cookies=forwarded_cookies)
    if response.status_code != 200:
        if not app.debug:
            raise Exception('Frame request returned an error code: {}.'.format(
                response.status_code))
        return
    if not response.text and not app.debug:
        raise Exception('Frame request returned an empty response.')
    assert response.headers['content-type'] == 'application/json'

    flask.g.frame_response = frame_response = flask.json.loads(response.text)
    flask.g.user_id = frame_response.get('user_id')
    flask.g.user_roles = frame_response.get('user_roles', [])
    flask.g.user_first_name = frame_response.get('user_first_name', [])
    flask.g.user_last_name = frame_response.get('user_last_name', [])
    flask.g.email = frame_response.get('email', [])
    flask.g.groups = frame_response.get('groups', [])
