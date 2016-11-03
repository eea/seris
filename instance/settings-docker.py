import os

SECRET_KEY = os.environ.get('SECRET_KEY')

DATABASE_URI = os.environ.get('DATABASE_URI')
FRAME_URL = os.environ.get('FRAME_URL')
HTTP_PROXIED = eval(os.environ.get('HTTP_PROXIED'))
HTTP_X_SCRIPT_NAME = os.environ.get('HTTP_X_SCRIPT_NAME')
ZOPE_TEMPLATE_CACHE = eval(os.environ.get('ZOPE_TEMPLATE_CACHE'))
FRAME_COOKIES = os.environ.get('FRAME_COOKIES')
MAIL_FAIL_SILENTLY = eval(os.environ.get('MAIL_FAIL_SILENTLY'))
DEFAULT_MAIL_SENDER = os.environ.get('DEFAULT_MAIL_SENDER')
ADMINISTRATOR_EMAILS = eval(os.environ.get('ADMINISTRATOR_EMAILS'))
