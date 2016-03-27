from flask import Flask, request, render_template
from flask_restful import Resource, Api
from pymongo import MongoClient, GEO2D
from flask_restful import fields, marshal_with, reqparse, inputs
from flask.ext.restful.utils import cors
from flask.ext.paginate import Pagination
import random
from bson.son import SON
import os
import datetime
from dateutil.parser import *


MONGOLAB_URL = os.environ['MONGOLAB_URL']
DEFAULT_HARVEST_DATE = datetime.datetime(2016, 1, 1, 0, 0, 0)

app = Flask(__name__)
api = Api(app)
api.decorators = [cors.crossdomain(origin='*', methods=['GET'],)]

REASONS = {
    '33(1)(a)': {'definition': 'contains information or matter the disclosure of which under this Act could reasonably be expected to cause damage to the security, defence or international relations of the Commonwealth', 'source': 'act'},
    '33(1)(b)': {'definition':  'contains information or matter: (i) that was communicated in confidence by, or on behalf of, a foreign government, an authority of a foreign government or an international organisation (the foreign entity) to the Government of the Commonwealth, to an authority of the Commonwealth or to a person who received the communication on behalf of the Commonwealth or an authority of the Commonwealth (the Commonwealth entity); and (ii) which the foreign entity advises the Commonwealth entity is still confidential; and (iii) the confidentiality of which it would be reasonable to maintain', 'source': 'act'},
    '33(1)(c)': {'definition': 'contains information or matter the disclosure of which under this Act would have a substantial adverse effect on the financial or property interests of the Commonwealth or of a Commonwealth institution and would not, on balance, be in the public interest', 'source': 'act'},
    '33(1)(d)': {'definition': 'contains information or matter the disclosure of which under this Act would constitute a breach of confidence', 'source': 'act'},
    '33(1)(e)(i)': {'definition': 'contains information or matter the disclosure of which under this Act would, or could reasonably be expected to prejudice the conduct of an investigation of a breach, or possible breach, of the law, or a failure, or possible failure, to comply with a law relating to taxation or prejudice the enforcement or proper administration of the law in a particular instance', 'source': 'act'},
    '33(1)(e)(ii)': {'definition': 'contains information or matter the disclosure of which under this Act would, or could reasonably be expected to disclose, or enable a person to ascertain, the existence or identity of a confidential source of information in relation to the enforcement or administration of the law', 'source': 'act'},
    '33(1)(e)(iii)': {'definition': 'contains information or matter the disclosure of which under this Act would, or could reasonably be expected to endanger the life or physical safety of any person', 'source': 'act'},
    '33(1)(f)(ii)': {'definition': 'contains information or matter the disclosure of which under this Act would, or could reasonably be expected to disclose lawful methods or procedures for preventing, detecting, investigating, or dealing with matters arising out of, breaches or evasions of the law the disclosure of which would, or would be reasonably likely to, prejudice the effectiveness of those methods or procedures', 'source': 'act'},
    '33(1)(f)(iii)': {'definition': 'contains information or matter the disclosure of which under this Act would, or could reasonably be expected to prejudice the maintenance or enforcement of lawful methods for the protection of public safety', 'source': 'act'},
    '33(1)(g)': {'definition': 'contains information or matter the disclosure of which under this Act would involve the unreasonable disclosure of information relating to the personal affairs of any person (including a deceased person)', 'source': 'act'},
    '33(1)(h)': {'definition': 'contains information or matter relating to trade secrets, or any other information or matter having a commercial value that would be, or could reasonably be expected to be, destroyed or diminished if the information or matter were disclosed', 'source': 'act'},
    '33(1)(j)': {'definition': 'contains information or matter (other than information or matter referred to in paragraph (h)) concerning a person in respect of his or her business or professional affairs or concerning the business, commercial or financial affairs of an organization or undertaking, being information or matter the disclosure of which would, or could reasonably be expected to, unreasonably affect that person adversely in respect of his or her lawful business or professional affairs or that organization or undertaking in respect of its lawful business, commercial or financial affairs', 'source': 'act'},
    '33(2)(a)': {'definition': 'of such a nature that it would be privileged from production in legal proceedings on the ground of legal professional privilege', 'source': 'act'},
    '33(2)(b)': {'definition': 'of such a nature that disclosure of the record would be contrary to the public interest', 'source': 'act'},
    '33(3)(a)(i)': {'definition': 'contains information or matter that relates to the personal affairs, or the business or professional affairs, of any person (including a deceased person)', 'source': 'act'},
    '33(3)(a)(ii)': {'definition': 'contains information or matter that relates to the business, commercial or financial affairs of an organization or undertaking', 'source': 'act'},
    '33(3)(b)': {'definition': 'there is in force a law relating to taxation that applies specifically to information or matter of that kind and prohibits persons referred to in that law from disclosing information or matter of that kind, whether the prohibition is absolute or is subject to exceptions or qualifications', 'source': 'act'},
    'Cabinet notebooks': {'definition': 'Cabinet notebooks (22A(1) a Cabinet notebook is in the open access period if a period of 50 years has elapsed since the end of the year ending on 31 December in which the Cabinet notebook came into existence).', 'source': 'recordsearch'},
    'Closed period': {'definition': 'Closed period', 'source': 'recordsearch'},
    'Court records': {'definition': 'Court records: not subject to access and appeal provisions of the Archives Act unless regulations have been made. [No regulations as at 1997.]', 'source': 'recordsearch'},
    'Destroyed': {'definition': 'Record destroyed in accordance with its relevant Records Disposal Authority', 'source': 'recordsearch'},
    'MAKE YOUR SELECTION': {'definition': '', 'source': ''},
    'NRF': {'definition': 'No records found [admininstrative]. A decision cannot be made on this item as it falls outside the provisions of the Archives Act 1983 and a decision cannot be made in relation to an access application.', 'source': 'recordsearch'},
    'Non Cwlth-depositor': {'definition': 'Non Commonwealth (personal/corporate) records - each application for access subject to approval of depositor.', 'source': 'recordsearch'},
    'Non Cwlth-no appeal': {'definition': 'Non Commonwealth (personal/corporate) records - decision not appealable.', 'source': 'recordsearch'},
    'Parliament Class A': {'definition': 'Parliamentary records not subject to the Archives Act: access subject to permission of Presiding Officer or in accordance with a Parliamentary practice. See Archives (Records of the Parliament) Regulations', 'source': 'recordsearch'},
    'Pre Access Recorder': {'definition': 'Pre Access Recorder non standard reasons for restriction.', 'source': 'recordsearch'},
    'Withheld pending adv': {'definition': 'This item has been withheld pending access advice from an agency/agencies.', 'source': 'recordsearch'}
}


def get_db():
    dbclient = MongoClient(MONGOLAB_URL)
    db = dbclient.get_default_database()
    return db


class Year(fields.Raw):
    def format(self, value):
        return value['date'].year


class DateString(fields.Raw):
    def format(self, value):
        return value['date_str']


class Start(fields.Raw):
    def format(self, value):
        return value['start_date']['date'].year


class End(fields.Raw):
    def format(self, value):
        return value['end_date']['date'].year


class Date(fields.Raw):
    def format(self, value):
        return value['start_date']['date'].isoformat()

item_fields = {}
item_fields['id'] = fields.Integer(attribute='_id')
item_fields['control_symbol'] = fields.String()
item_fields['title'] = fields.String()
item_fields['contents_dates'] = DateString()
item_fields['start_year'] = Start(attribute='contents_dates')
item_fields['end_year'] = End(attribute='contents_dates')
item_fields['reasons'] = fields.List(fields.String)
item_fields['date_of_decision'] = Date(attribute='access_decision')
item_fields['series'] = fields.String()
item_fields['series_title'] = fields.String()


def convert_harvest_date(harvest=None):
    try:
        dates = harvest.split('-')
        harvest_date = datetime.datetime(int(dates[0]), int(dates[1]), int(dates[2]), 0, 0, 0)
    except:
        harvest_date = DEFAULT_HARVEST_DATE
    return harvest_date


@app.route('/')
def home():
    harvest_date = convert_harvest_date()
    db = get_db()
    items = db.items.find({'random_id': {'$near': [random.random(), 0]}}).limit(20)
    harvest = db.harvests.find_one({'harvest_date': harvest_date})
    return render_template('home.html', items=items, harvest=harvest)


@app.route('/about/')
def about():
    return render_template('about.html')


@app.route('/examples/')
def examples():
    return render_template('examples.html')


@app.route('/ages/')
def get_ages():
    harvest = request.args.get('harvest', None)
    harvest_date = convert_harvest_date(harvest)
    now = datetime.datetime.now().year
    db = get_db()
    total = db.harvests.find_one({'harvest_date': harvest_date})['total']
    years = db.aggregates.find_one({'harvest_date': harvest_date, 'agg_type': 'year_totals'})
    x = []
    y = []
    text = []
    for year in years['results']:
        y.append(year['total'])
        x.append(year['year'])
        text.append('{} closed files'.format(year['total']))
    data = [{'x': x, 'y': y, 'text': text, 'hoverinfo': 'x+text', 'type': 'bar', 'marker': {'color': '#800080'}}]
    ends = db.aggregates.find_one({'harvest_date': harvest_date, 'agg_type': 'end_totals'})
    count = 0
    x = []
    y = []
    text = []
    for year in ends['results'][::-1]:
        new_total = total - count
        count += year['total']
        x.append(now - year['year'])
        y.append(count)
        text.append('{} ({:.2f}%) closed files are more than {} years old'.format(new_total, (new_total / float(total)) * 100, now - year['year']))
    open_data = [{'x': x, 'y': y, 'text': text, 'hoverinfo': 'text', 'fill': 'tozeroy', 'type': 'scatter', 'marker': {'color': '#800080'}}]
    open_date = datetime.datetime(now - 21, 12, 31, 0, 0, 0)
    print open_date
    open_total = db.items.find({'harvests': harvest_date, 'contents_dates.end_date.date': {'$lte': open_date}}).count()
    print open_total
    return render_template('ages.html', years=years, data=data, open_data=open_data, now=now, open_total=open_total, total=total)


@app.route('/reasons/')
def get_reasons():
    harvest = request.args.get('harvest', None)
    harvest_date = convert_harvest_date(harvest)
    db = get_db()
    reasons = db.aggregates.find_one({'harvest_date': harvest_date, 'agg_type': 'reason_totals'})
    x = []
    y = []
    text = []
    for index, reason in enumerate(reasons['results']):
        reasons['results'][index]['definition'] = REASONS[reason['reason']]['definition']
        y.append(reason['reason'])
        x.append(reason['total'])
        text.append('{} closed files'.format(reason['total']))
    data = [{'x': x[::-1], 'y': y[::-1], 'text': text[::-1], 'hoverinfo': 'y+text', 'type': 'bar', 'orientation': 'h', 'marker': {'color': '#800080'}}]
    return render_template('reasons.html', reasons=reasons, data=data)


@app.route('/reasons/<reason_id>/')
def get_reason(reason_id):
    harvest = request.args.get('harvest', None)
    harvest_date = convert_harvest_date(harvest)
    db = get_db()
    reason = db.aggregates.find_one({'harvest_date': harvest_date, 'reason': reason_id})
    reason['reason'] = reason_id
    reason['definition'] = REASONS[reason_id]['definition']
    reason['source'] = REASONS[reason_id]['source']
    x = []
    y = []
    text = []
    dodgy = False
    for year in reason['year_totals']:
        if year['year'] == 1800:
            dodgy = True
        y.append(year['total'])
        x.append(year['year'])
        text.append('{} closed files'.format(year['total']))
    year_data = [{'x': x, 'y': y, 'text': text, 'hoverinfo': 'x+text', 'type': 'bar', 'marker': {'color': '#800080'}}]
    count = 0
    total = reason['total']
    now = datetime.datetime.now().year
    x = []
    y = []
    text = []
    for result in reason['end_totals'][::-1]:
        new_total = total - count
        count += result['total']
        x.append(now - result['year'])
        y.append(count)
        text.append('{} ({:.2f}%) of closed files are more than {} years old'.format(new_total, (new_total / float(total)) * 100, now - result['year']))
    open_data = [{'x': x, 'y': y, 'text': text, 'hoverinfo': 'text', 'fill': 'tozeroy', 'type': 'scatter', 'marker': {'color': '#800080'}}]
    x = []
    y = []
    text = []
    for result in reason['series'][:50]:
        y.append(result['total'])
        x.append(result['series'])
        text.append('{} closed files'.format(result['total']))
    series_data = [{'x': x, 'y': y, 'text': text, 'hoverinfo': 'x+text', 'type': 'bar', 'marker': {'color': '#800080'}}]
    count = 0
    total_age = 0
    for result in reason['decisions']:
        if result['year'] != 1800:
            total_age += (now - result['year']) * result['total']
            count += result['total']
    reason['decision_age'] = total_age / count
    items = db.items.find({'random_id': {'$near': [random.random(), 0]}, 'reasons': reason_id, 'harvests': harvest_date}).limit(20)
    return render_template('reason.html', reason=reason, harvest=harvest_date, year_data=year_data, open_data=open_data, now=now, series_data=series_data, items=items, dodgy=dodgy)


@app.route('/series/')
def get_series_chart():
    harvest = request.args.get('harvest', None)
    harvest_date = convert_harvest_date(harvest)
    db = get_db()
    series_totals = db.aggregates.find_one({'harvest_date': harvest_date, 'agg_type': 'series_totals'})
    results = series_totals['results'][:50]
    x = []
    y = []
    text = []
    for index, series in enumerate(results):
        results[index]['title'] = ''
        y.append(series['series'])
        x.append(series['total'])
        text.append('{} closed files'.format(series['total']))
    data = [{'x': x[::-1], 'y': y[::-1], 'text': text[::-1], 'hoverinfo': 'y+text', 'type': 'bar', 'orientation': 'h', 'marker': {'color': '#800080'}}]
    return render_template('series_chart.html', series=results, data=data)


@app.route('/series/list/')
def get_series_list():
    results_per_page = 100
    harvest = request.args.get('harvest', None)
    reason = request.args.get('reason', None)
    harvest_date = convert_harvest_date(harvest)
    db = get_db()
    if reason:
        series_totals = db.aggregates.find_one({'harvest_date': harvest_date, 'agg_type': 'reason', 'reason': reason})['series']
    else:
        series_totals = db.aggregates.find_one({'harvest_date': harvest_date, 'agg_type': 'series_totals'})['results']
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    start = (page-1)*results_per_page
    end = start + results_per_page
    results = series_totals[start:end]
    total = len(series_totals)
    pagination = Pagination(page=page, total=total, record_name='series', bs_version=3, per_page=results_per_page)
    return render_template('series_list.html', series=results, pagination=pagination, reason=reason)


@app.route('/series/<series_id>/')
def get_series(series_id):
    series_id = series_id.replace('_', '/')
    harvest = request.args.get('harvest', None)
    harvest_date = convert_harvest_date(harvest)
    db = get_db()
    series_totals = db.aggregates.find_one({'harvest_date': harvest_date, 'series': series_id})
    dodgy = False
    x = []
    y = []
    text = []
    for year in series_totals['year_totals']:
        if year['year'] == 1800:
            dodgy = True
        y.append(year['total'])
        x.append(year['year'])
        text.append('{} closed files'.format(year['total']))
    year_data = [{'x': x, 'y': y, 'text': text, 'hoverinfo': 'x+text', 'type': 'bar', 'marker': {'color': '#800080'}}]
    count = 0
    total = series_totals['total']
    now = datetime.datetime.now().year
    x = []
    y = []
    text = []
    for result in series_totals['end_totals'][::-1]:
        new_total = total - count
        count += result['total']
        x.append(now - result['year'])
        y.append(count)
        text.append('{} ({:.2f}%) of closed files are more than {} years old'.format(new_total, (new_total / float(total)) * 100, now - result['year']))
    open_data = [{'x': x, 'y': y, 'text': text, 'hoverinfo': 'text', 'fill': 'tozeroy', 'type': 'scatter', 'marker': {'color': '#800080'}}]
    x = []
    y = []
    text = []
    for index, reason in enumerate(series_totals['reasons']):
        series_totals['reasons'][index]['definition'] = REASONS[reason['reason']]['definition']
        y.append(reason['reason'])
        x.append(reason['total'])
        text.append('{} closed files'.format(reason['total']))
    reasons_data = [{'x': x[::-1], 'y': y[::-1], 'text': text[::-1], 'hoverinfo': 'y+text', 'type': 'bar', 'orientation': 'h', 'marker': {'color': '#800080'}}]
    series = db.series.find_one({'identifier': series_id})
    end_date = datetime.datetime(now-20, 12, 31, 0, 0, 0)
    total_open = db.items.find({'harvests': harvest_date, 'contents_dates.end_date.date': {'$lte': end_date}, 'series': series_id}).count()
    items = db.items.find({'random_id': {'$near': [random.random(), 0]}, 'series': series_id, 'harvests': harvest_date}).limit(20)
    return render_template('series.html', series=series, totals=series_totals, harvest=harvest_date, year_data=year_data, open_data=open_data, reasons_data=reasons_data, total_open=total_open, now=now, items=items, dodgy=dodgy)


@app.route('/items/')
def get_items():
    db = get_db()
    results_per_page = 100
    harvest_id = request.args.get('harvest', None)
    harvest_date = convert_harvest_date(harvest_id)
    reasons_list = db.aggregates.find_one({'harvest_date': harvest_date, 'agg_type': 'reason_totals'})['results']
    series_list = sorted([series['series'] for series in db.aggregates.find_one({'harvest_date': harvest_date, 'agg_type': 'series_totals'})['results']])
    now = datetime.datetime.now().year
    years = [year for year in range(1800, now)]
    q = request.args.get('q', None)
    sort = request.args.get('sort', 'series')
    start_year = request.args.get('start_year', None)
    start_direction = request.args.get('start_direction', 'after')
    end_year = request.args.get('end_year', None)
    end_direction = request.args.get('end_direction', 'before')
    content_year = request.args.get('content_year', None)
    series = request.args.get('series', None)
    reasons = request.args.getlist('reasons')
    reasons_match = request.args.get('reasons_match', 'any')
    decision_after = request.args.get('decision_after', None)
    decision_before = request.args.get('decision_before', None)
    age = request.args.get('age', None)
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    query = {}
    query['harvests'] = harvest_date
    if q:
        query['$text'] = {'$search': q}
    if reasons:
        if reasons_match == 'any':
            query['reasons'] = {'$in': reasons}
        elif reasons_match == 'all':
            query['reasons'] = {'$all': reasons}
        elif reasons_match == 'exact':
                query['reasons'] = reasons
    if start_year:
        start_year = int(start_year)
        if start_direction == 'before':
            start_date = datetime.datetime(start_year, 12, 31, 0, 0, 0)
            query['contents_dates.start_date.date'] = {'$lte': start_date}
        elif start_direction == 'after':
            start_date = datetime.datetime(start_year, 1, 1, 0, 0, 0)
            query['contents_dates.start_date.date'] = {'$gte': start_date}
    if end_year:
        end_year = int(end_year)
        if end_direction == 'before':
            end_date = datetime.datetime(end_year, 12, 31, 0, 0, 0)
            query['contents_dates.end_date.date'] = {'$lte': end_date}
        elif end_direction == 'after':
            end_date = datetime.datetime(end_year, 1, 1, 0, 0, 0)
            query['contents_dates.end_date.date'] = {'$gte': end_date}
    if content_year:
        content_year = int(content_year)
        query['contents_dates.start_date.date'] = {'$lte': datetime.datetime(content_year, 12, 31, 0, 0, 0)}
        query['contents_dates.end_date.date'] = {'$gte': datetime.datetime(content_year, 1, 1, 0, 0, 0)}
    if age:
        age = int(age)
        end_date = datetime.datetime(now-age, 12, 31, 0, 0, 0)
        query['contents_dates.end_date.date'] = {'$lte': end_date}
    if series:
        query['series'] = series
    if decision_after and decision_before:
        decision_after_date = parse(decision_after)
        decision_before_date = parse(decision_before)
        query['access_decision.start_date.date'] = {'$gte': decision_after_date, '$lte': decision_before_date}
    elif decision_after:
        decision_after_date = parse(decision_after)
        query['access_decision.start_date.date'] = {'$gte': decision_after_date}
    elif decision_before:
        decision_before_date = parse(decision_before)
        query['access_decision.start_date.date'] = {'$lte': decision_before_date}
    if sort == 'series':
        order_by = [['series', 1], ['control_symbol', 1]]
    elif sort == 'oldest':
        order_by = [['contents_dates.start_date.date', 1]]
    elif sort == 'youngest':
        order_by = [['contents_dates.start_date.date', -1]]
    elif sort == 'decisions':
        order_by = [['access_decision.start_date.date', 1]]
    items = db.items.find(query).sort(order_by).skip((page-1)*results_per_page).limit(results_per_page)
    total = db.items.find(query).count()
    pagination = Pagination(page=page, total=total, record_name='items', bs_version=3, per_page=results_per_page)
    return render_template('items.html', items=items, pagination=pagination, reasons_list=reasons_list, series_list=series_list, years=years, q=q, reasons=reasons, series=series, start_year=start_year, end_year=end_year, age=age, sort=sort, reasons_match=reasons_match, decision_after=decision_after, decision_before=decision_before, start_direction=start_direction, end_direction=end_direction, content_year=content_year)


@app.route('/items/<id>/')
def get_item(id):
    db = get_db()
    harvest_date = convert_harvest_date()
    item = db.items.find_one({'identifier': id})
    start = item['contents_dates']['start_date']['date']
    end = item['contents_dates']['end_date']['date']
    decision = item['access_decision']['start_date']['date']
    now = datetime.datetime.now()
    item['age'] = (now-start).days/365
    if (now.year - end.year) > 21:
        item['open_period'] = True
    item['decision_age'] = (now-decision).days/float(365)
    return render_template('item.html', item=item, harvest=harvest_date)


@app.route('/harvests/')
def get_harvests():
    db = get_db()
    harvests = list(db.harvests.find().sort('harvest_date', -1))
    return render_template('harvests.html', harvests=harvests)


class GetItems(Resource):
    def get(self):
        response = {}
        db = get_db()
        collection = db.items
        # collection.create_index([('random_id', GEO2D)])
        parser = reqparse.RequestParser()
        parser.add_argument('n', type=int, default=20)
        parser.add_argument('s', type=int, default=0)
        parser.add_argument('contents_year', type=int)
        parser.add_argument('reason', type=str, action='append')
        parser.add_argument('series', type=str)
        parser.add_argument('order_by', type=str)
        parser.add_argument('decision_year', type=int)
        args = parser.parse_args()
        if args['n'] > 100:
            number = 100
        else:
            number = args['n']
        query = {}
        print args
        if args['contents_year']:
            contents_date = datetime.datetime(args['contents_year'], 1, 1, 0, 0, 0)
            query['contents_dates.start_date.date'] = {'$lte': contents_date}
            query['contents_dates.end_date.date'] = {'$gte': contents_date}
        if args['decision_year']:
            decision_date_start = datetime.datetime(args['decision_year'], 1, 1, 0, 0, 0)
            decision_date_end = datetime.datetime(args['decision_year'], 12, 31, 0, 0, 0)
            query['access_decision.start_date.date'] = {'$gte': decision_date_start, '$lte': decision_date_end}
        if args['reason']:
            query['reasons'] = {'$all': args['reason']}
        if args['series']:
            query['series'] = args['series']
        if args['order_by'] == 'random':
            query['random_id'] = {'$near': [random.random(), 0]}
        items = list(collection.find(query).limit(number).skip(args['s']))
        response['total'] = collection.find(query).count()
        response['results'] = marshal(items, item_fields)
        response['s'] = args['s']
        response['n'] = number
        return response


class GetReasons(Resource):
    def get(self):
        response = {}
        db = get_db()
        collection = db.items
        parser = reqparse.RequestParser()
        parser.add_argument('decision_year', type=int)
        parser.add_argument('contents_year', type=int)
        parser.add_argument('harvest', type=inputs.date)
        args = parser.parse_args()
        pipeline = []
        if args['decision_year'] or args['contents_year']:
            if args['decision_year']:
                decision_date_start = datetime.datetime(args['decision_year'], 1, 1, 0, 0, 0)
                decision_date_end = datetime.datetime(args['decision_year'], 12, 31, 0, 0, 0)
                pipeline.append({'$match': {'harvests': args['harvest'], 'access_decision.start_date.date': {'$gte': decision_date_start, '$lte': decision_date_end}}})
            if args['contents_year']:
                contents_date = datetime.datetime(args['contents_year'], 1, 1, 0, 0, 0)
                pipeline += [{'$match': {'harvests': args['harvest'], 'contents_dates.start_date.date': {'$lte': contents_date}}}, {'$match': {'contents_dates.end_date.date': {'$gte': contents_date}}}]
            pipeline += [
                {"$unwind": "$reasons"},
                {"$group": {"_id": "$reasons", "total": {"$sum": 1}}},
                {"$project": {"_id": 0, "reason": "$_id", "total": "$total"}},
                {'$sort': {'reason': 1}}
            ]
            items = list(collection.aggregate(pipeline))
        else:
            harvest = db.harvests.find_one({'harvest_date': args['harvest']})
            items = harvest['total_reasons']
        response = {'results': items}
        response['total'] = len(items)
        return response


class GetReason(Resource):
    def get(self, reason):
        db = get_db()
        parser = reqparse.RequestParser()
        parser.add_argument('harvest', type=inputs.date)
        args = parser.parse_args()
        harvest = db.harvests.find_one({'harvest_date': args['harvest']})
        results = harvest['reasons'][reason]
        results['reason'] = reason
        return results


class GetDecisions(Resource):
    def get(self):
        pipeline = [
            {"$group": {"_id": {"$year": "$access_decision.start_date.date"}, "total": {"$sum": 1}}},
            {"$project": {"_id": 0, "decision_year": "$_id", "total": "$total"}},
            {'$sort': {'decision_year': -1}}
        ]
        items = get_items()
        return list(items.aggregate(pipeline))


api.add_resource(GetItems, '/items')
api.add_resource(GetReasons, '/reasons')
api.add_resource(GetReason, '/reasons/<reason>')
api.add_resource(GetDecisions, '/decisions')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
