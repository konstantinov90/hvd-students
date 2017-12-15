import os
import asyncio
import datetime
import hashlib
import traceback

from aiohttp import web
import aiohttp_jinja2
from aiohttp_auth import auth

from hvd_calendar import get_workdays_delta
import months
import app_log
log = app_log.get_logger()

CRITICAL_TIMEDELTA = datetime.timedelta(days=-1, hours=13)


async def process_response(self, request, response):
    """Called to perform any processing of the response required.

    This function stores any cookie data in the COOKIE_AUTH_KEY as a
    cookie in the response object. If the value is a empty string, the
    associated cookie is deleted instead.

    This function requires the response to be a aiohttp Response object,
    and assumes that the response has not started if the remember or
    forget functions are called during the request.

    Args:
        request: aiohttp Request object.
        response: response object returned from the handled view

    Raises:
        RuntimeError: Raised if response has already started.
    """
    COOKIE_AUTH_KEY = 'aiohttp_auth.auth.CookieTktAuthentication'
    await super(auth.cookie_ticket_auth.CookieTktAuthentication, self).process_response(request, response)
    if COOKIE_AUTH_KEY in request:
        if hasattr(response, 'started') and response.started:
            raise RuntimeError("Cannot save cookie into started response")

        cookie = request[COOKIE_AUTH_KEY]
        if cookie == '':
            response.del_cookie(self.cookie_name)
        else:
            response.set_cookie(self.cookie_name, cookie)

auth.cookie_ticket_auth.CookieTktAuthentication.process_response = process_response

import jinja2
from motor import motor_asyncio as motor
import xlsxwriter
import aiofiles
from multidict import MultiDict

import rest
import settings as S

auth_policy = auth.CookieTktAuthentication(os.urandom(32), 6000000, include_ip=True)
auth_middleware = auth.auth_middleware(auth_policy)


@aiohttp_jinja2.template('sign-up.html')
async def ask_for_password(request):
    msg = ''
    if request.query.get('msg') == 'unequal-pwds':
        msg = 'пароль подтвержден неправильно!'
    return {
        'id': request.query.get('id', ''),
        'msg': msg,
    }

@aiohttp_jinja2.template('login.html')
async def login(request):
    if request['user']:
        return web.HTTPFound('/')
    msg = ''
    if request.query.get('msg') == 'wrong-pwd':
        msg = 'Введен неправильный пароль'
    return {'msg': msg}


@aiohttp_jinja2.template('index.html')
async def index(request):
    user = request['user']
    if not user:
        return web.HTTPFound('/login')
    if 'pwd' not in user:
        return web.HTTPFound('/sign-up')

    days = await request.app['db'].timetable.find().sort([('day', 1)]).to_list(None)
    for day in days:
        for key, period in list(day['periods'].items()):
            if user['group'] not in period['groups'] and user['name'] != 'super':
                del day['periods'][key]
    days = [day for day in days if day['periods']]
    for day in days:
        day['day_str'] = f'{day["day"]:%d} {months.MONTHS[day["day"].month-1]} {day["day"]:%Y} г.'

    return {
        "days": days,
        "user": user,
        "months": months.MONTHS,
        "epoch": datetime.datetime.utcfromtimestamp(0),
    }

async def static(request):
    filename = request.match_info.get('filename')
    if filename:
        return web.FileResponse(f'static/{filename}')

async def heartbeat(request):
    while request.query['hash'] == request.app['container']['hash']:
        try:
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
    return web.Response(text=request.app['container']['hash'], headers=MultiDict({
        'Cache-Control': 'No-Cache'
    }))

async def report(request):
    db = request.app['db']

    filename = 'сводка.xlsx'

    wb = xlsxwriter.Workbook(filename, {'default_date_format': 'dd-mm-yyyy'})
    ws = wb.add_worksheet('сводка')

    ws.write_row(0, 0, ('дата', 'пары', 'группы', 'номер л/р', 'всего мест', 'записавшихся', 'ФИО', 'группа'))

    i = 1

    students = await db.users.find().to_list(None)

    async for day in db.timetable.find().sort([("day", 1)]):
        for period_name, period in day['periods'].items():
            per_name = '1-2 пары 09:20 - 12:45' if period_name == 'first' else '3-4 пары 13:45 - 17:10'
            groups = ', '.join(period['groups'])
            ws.write_row(i,0, (day['day'], per_name, groups,))
            i += 1
            for lab in period['labs']:
                ws.write_row(i, 3, (lab['_id'], lab['quota'], lab['students_registered']))
                i += 1
                for student in students:
                    if student['labs'].get(lab['_id']) == {'day': day['day'], 'period': period_name}:
                        ws.write_row(i, 6, (student['name'], student['group'],))
                        i += 1
    wb.close()

    cnt_dsp = f'attachment; filename="{filename}"'
    content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    resp = web.StreamResponse(headers=MultiDict({
        'CONTENT-DISPOSITION': cnt_dsp,
        'Content-Type': content_type
    }))
    resp.content_length = os.stat(filename).st_size
    await resp.prepare(request)
    async with aiofiles.open(filename, 'rb') as fd:
        resp.write(await fd.read())
    os.remove(filename)
    return resp


@web.middleware
async def error_middleware(request, handler):
    db = request.app['db']
    try:
        return await handler(request)
    except web.HTTPClientError as resp:
        return resp
    except Exception as e:
        tb = ''.join(traceback.format_tb(e.__traceback__))
        await db.log.insert({
            'level': 'error',
            'client_ip': str(request.headers.get('X-Forwarder-For', request.remote)),
            'url': str(request.rel_url),
            'user_agent': request.headers['User-Agent'],
            'timestamp': datetime.datetime.now(),
            'traceback': tb,
        })
        log.error(f'{e.__class__} {tb}')
        # return web.HTTPInternalServerError(text=''.join(traceback.format_tb(e.__traceback__)))
        return web.HTTPInternalServerError(text="""
Произошла непредвиденная ошибка на сервере, с этим уже разбираются.
Пока можете написать на hvdstudents@yandex.ru
""")

@web.middleware
async def access_logger(request, handler):
    user = request['user']
    db = request.app['db']
    if user:
        await db.log.insert({
            'level': 'info',
            'user': user['_id'],
            'client_ip': str(request.headers.get('X-Forwarded-For', request.remote)),
            'url': str(request.rel_url),
            'user_agent': request.headers['User-Agent'],
            'timestamp': datetime.datetime.now(),
        })
        msg = f'''
            user = {user['_id']}
            client ip = {request.remote}
            url = {request.rel_url}
            user agent = {request.headers['User-Agent']}'''
        log.info(msg)
    
    return await handler(request)

@web.middleware
async def response_logger(request, handler):
    resp = await handler(request)
    if isinstance(resp, dict):
        db = request.app['db']
        await db.log.insert(resp)

        msg = f'''
            user = {resp['user']}
            event = {resp['event']}
            day = {resp['entity']['day']}
            period = {resp['entity']['period']}
            lab = {resp['entity']['lab']}'''
        log.info(msg)

        resp = web.Response(text='ok')
    return resp

@web.middleware
async def user_data_middleware(request, handler):
    db = request.app['db']
    user_id = await auth.get_auth(request)
    if user_id:
        user = await db.users.find_one({'_id': int(user_id)})
        # user['labs'] = { k: lab for k, lab in user['labs'].items() if lab.get('blocked_until', datetime.datetime.max) > datetime.datetime.now() }
    request['user'] = user if user_id else None
    
    return await handler(request)


def make_app(loop):
    app = web.Application(
        loop=loop,
        middlewares=[
            auth_middleware,
            user_data_middleware,
            access_logger,
            response_logger,
            error_middleware,
        ]
    )
    app.router.add_get('/', index)
    # app.router.add_get('/static/{filename}', static)
    app.router.add_static('/static', 'static', show_index=False)

    app.router.add_post('/rest/send_password', rest.sign_up)
    app.router.add_post('/rest/register', rest.register)
    app.router.add_post('/rest/unregister', rest.unregister)
    app.router.add_post('/rest/login', rest.login)
    app.router.add_get('/login', login)
    app.router.add_get('/sign-up', ask_for_password)
    app.router.add_get('/heartbeat', heartbeat)
    app.router.add_get('/get_report', report)

    # app.router.add_get('/{name}', handle)

    aiohttp_jinja2.setup(app,
        loader=jinja2.FileSystemLoader('templates')
    )

    db = motor.AsyncIOMotorClient(S.mongo['url'])[S.mongo['db']]
    app.update(db=db, running=True, container={'hash': ''}, hash_analyzer=None)

    async def db_auth(app):
        await app['db'].authenticate(S.mongo['username'], S.mongo['pwd'])

    async def run_db_hash_analyzer(app):
        app['hash_analyzer'] = asyncio.ensure_future(db_hash_analyzer(app))

    async def db_hash_analyzer(app):
        while app['running']:
            try:
                data = await app['db'].timetable.find().to_list(None)
                app['container']['hash'] = hashlib.md5(str(data).encode()).hexdigest()
            finally:
                await asyncio.sleep(1)

    async def set_timetable_critical_dates(app):
        db = app['db']
        days = await db.timetable.find().to_list(None)
        for day in days:
            await db.timetable.update_one({'_id': day['_id']}, {
                '$set': {
                    'critical_time': day['day'] + CRITICAL_TIMEDELTA,
                    'block_until': get_workdays_delta(day['day'], 2),
                }   
            })

    async def shutdown(app):
        app['running'] = False
        await app['hash_analyzer']

    app.on_startup.append(db_auth)
    app.on_startup.append(run_db_hash_analyzer)
    app.on_startup.append(set_timetable_critical_dates)
    app.on_shutdown.append(shutdown)

    return app

web.run_app(make_app(asyncio.get_event_loop()), port=S.port)