#!/usr/bin/env python

import os
import flask
import logging
import flaskext.script
import database
from raven.contrib.flask import Sentry
import sparql
import simplejson as json

default_config = {
    'DATABASE_URI': 'postgresql://localhost/reportdb',
    'TESTING_DATABASE_URI': 'postgresql://localhost/reportdb_test',
    'HTTP_PROXIED': False,
    'FRAME_URL': None,
}


log = logging.getLogger(__name__)


def create_app():
    import views

    app = flask.Flask(__name__, instance_relative_config=True)
    app.config.update(default_config)
    app.config.from_pyfile('settings.py', silent=True)

    _my_extensions = app.jinja_options["extensions"] + ["jinja2.ext.do"]
    app.jinja_options = dict(app.jinja_options, extensions=_my_extensions)

    database.initialize_app(app)
    views.register_on(app)

    if app.config["HTTP_PROXIED"]:
        from revproxy import ReverseProxied
        app.wsgi_app = ReverseProxied(app.wsgi_app, app.config)

    if app.config.get("SENTRY_DSN"):
        sentry = Sentry()
        sentry.init_app(app)

    return app


def _load_json(name):
    with open(os.path.join(os.path.dirname(__file__), name), "rb") as f:
        return json.load(f)

manager = flaskext.script.Manager(create_app)


@manager.command
def update_country_names():
    SPARQL_QUERY = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX eea: <http://rdfdata.eionet.europa.eu/eea/ontology/>

            SELECT DISTINCT ?code ?countryname ?publishingCode
              IF(bound(?eumember),'Yes','') AS ?eu
              IF(bound(?eeamember),'Yes','') AS ?eea
              IF(bound(?eionetmember),'Yes','') AS ?eionet
              IF(bound(?eun22member),'Yes','') AS ?eun22
            WHERE {
              ?ucountry a eea:Country ;
                        eea:code ?code;
                        eea:publishingCode ?publishingCode;
                        rdfs:label ?countryname
             OPTIONAL { <http://rdfdata.eionet.europa.eu/eea/countries/EU> skos:member ?ucountry, ?eumember }
             OPTIONAL { <http://rdfdata.eionet.europa.eu/eea/countries/EUN22> skos:member ?ucountry, ?eun22member }
             OPTIONAL { <http://rdfdata.eionet.europa.eu/eea/countries/EEA> skos:member ?ucountry, ?eeamember }
             OPTIONAL { <http://rdfdata.eionet.europa.eu/eea/countries/EIONET> skos:member ?ucountry, ?eionetmember }
            }"""
    SPARQL_ENDPOINT = 'http://semantic.eea.europa.eu/sparql'

    s = sparql.Service(SPARQL_ENDPOINT)
    results = [i for i in s.query(SPARQL_QUERY).fetchone()]
    countries = {}
    for item in results:
        countries[item[0].value.lower()] = item[1].value
    f = open(("refdata/countries.json"), "w")
    json.dump(countries, f)
    f.close()


@manager.command
def migrate_country_name_to_code():
    session = database.get_session()
    countries = _load_json('refdata/countries.json')
    old_countries = _load_json('refdata/old_countries.json')
    country_mapping = {}
    for k, v in countries.items():
        country_mapping[v] = k
    country_mapping.update(old_countries)
    for row in database.get_all_reports():
        modified = False
        for index in range(0, len(country_mapping) + 1):
            country_name = row.get('header_country_' + str(index))
            if country_name and country_name in country_mapping.keys():
                row['header_country_' + str(index)] = country_mapping[country_name]
                modified = True
        if modified:
            session.save(row)
            session.commit()


@manager.command
def resetdb():
    database.get_session().drop_all()


@manager.command
def syncdb():
    database.get_session().create_all()


@manager.command
def import_seris():
    """
    Imported fields:
        u'details_original_name'
        u'format_availability_url'
        'details_translated_in_0'
        u'details_publisher'
        'header_country_0'
        u'format_date_of_last_update'
        u'details_english_name'
        u'format_report_type'
        'details_original_language_0'
        u'short_description'
    """

    from seris_old import SERIS_DATA
    from schema import _load_json
    countries_mapping = _load_json("refdata/seris_old_countries_mapping.json")
    countries_list = _load_json("refdata/countries_list.json")
    countries = [pair[0] for pair in countries_list]
    imported = 0
    skipped = 0
    for country, reports in SERIS_DATA.items():
        if country == 'eea' or countries_mapping[country] in countries:
            for form_data in reports:
                report_row = database.ReportRow()
                seris_review_row = database.SerisReviewRow()
                session = database.get_session()

                for k, v in form_data.items():
                    if v is None:
                        del(form_data[k])
                found = False
                for count in range(0, 100):
                    header_country = form_data.get('header_country_%s' % count)
                    if header_country not in countries:
                        if header_country:
                            del(form_data['header_country_%s' % count])
                    else:
                        found = True
                if not found:
                    if country == 'eea':
                        print ('Skipped report %s from eea: '
                               'countries not in scope' %
                               form_data.get('details_original_name'))
                        skipped += 1
                        continue
                    else:
                        form_data['header_country_0'] = countries_mapping[
                            country]

                if country == 'eea':
                    form_data['header_region_0'] = (
                        'European Environment Agency')
                if form_data.get('category') == 'National portal':
                    form_data['format_report_type'] = 'portal (dynamic source)'
                try:
                    int(form_data.get('format_date_of_publication'))
                except ValueError:
                    print 'Report %s in country %s - invalid year "%s"' % (
                        form_data.get('details_original_name'), country,
                        form_data.get('format_date_of_publication'))
                except TypeError:
                    pass
                report_schema = schema.ReportSchema.from_flat(form_data)
                seris_review_schema = schema.SerisReviewSchema.from_flat(
                    form_data)

                report_row.update(report_schema.flatten())
                uploader = 'Imported from SERIS 1'
                report_row['header_uploader'] = uploader
                report_row['header_upload_date'] = '01 Jan 1999, 00:00'
                session.save(report_row)
                seris_review_schema['report_id'].set(report_row.id)

                # Review part
                seris_review_row.clear()
                seris_review_row.update(seris_review_schema.flatten())
                session.save(seris_review_row)

                imported += 1
                session.commit()
    print '%s reports imported' % imported
    print '%s reports skipped' % skipped


def _debug_log(name):
    import logging
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    log.addHandler(logging.StreamHandler())


if __name__ == '__main__':
    import schema
    schema.register_handler_for_empty()
    manager.run()
