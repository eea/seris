import flask
from flask.ext.sendmail import Mail, Message

app = flask.Flask(__name__)
mail = Mail(app)


def send_mail(subject, recipients, html_body, text_body=None):
    msg = Message(subject=subject, recipients=recipients, charset='utf-8')
    if text_body:
        msg.body = text_body
    msg.html = html_body
    mail.send(msg)


def send_notification_mail(report_url, report_name, action,
                           contributor_profile, contributor_name,
                           contributor_id):
    msg = flask.render_template(
        'notification_email.html',
        **{'report_url': report_url,
           'report_name': report_name,
           'action': action,
           'contributor_profile': contributor_profile,
           'contributor_name': contributor_name,
           'contributor_id': contributor_id,
           }
        )
    send_mail('Report %s' % action,
              flask.current_app.config['ADMINISTRATOR_EMAILS'],
              msg)
