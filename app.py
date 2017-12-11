import os
import asyncio
import hashlib

from aiohttp import web
import aiohttp_jinja2
from aiohttp_auth import auth

import months

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

@aiohttp_jinja2.template('login.html')
async def login(request):
    if (await auth.get_auth(request)):
        return web.HTTPFound('/')
    return {}


@aiohttp_jinja2.template('index.html')
async def index(request):
    user_id = await auth.get_auth(request)
    if not user_id:
        return web.HTTPFound('/login')
    user = (await request.app['db'].users.find({'_id': int(user_id)}).to_list(None))[0]

    days = await request.app['db'].timetable.find().sort([('day', 1)]).to_list(None)
    for day in days:
        for key, period in list(day['periods'].items()):
            if user['group'] not in period['groups']:
                del day['periods'][key]
    days = [day for day in days if day['periods']]
    for day in days:
        day['day_str'] = f'{day["day"]:%d} {months.MONTHS[day["day"].month-1]} {day["day"]:%Y} г.'

    return {
        "days": days,
        "user": user,
        "months": months.MONTHS,
    }

async def static(request):
    filename = request.match_info.get('filename')
    if filename:
        return web.FileResponse(f'static/{filename}')

async def heartbeat(request):
    while request.query['hash'] == request.app['container']['hash']:
        await asyncio.sleep(0.1)
    return web.Response(text=request.app['container']['hash'])

async def report(request):
    db = request.app['db']

    filename = 'сводка.xlsx'

    wb = xlsxwriter.Workbook(filename, {'default_date_format': 'dd-mm-yyyy'})
    ws = wb.add_worksheet('сводка')

    ws.write_row(0, 0, ('дата', 'пары', 'группы', 'номер л/р', 'всего мест', 'записавшихся', 'ФИО', 'группа'))

    i = 1

    students = await db.users.find().to_list(None)

    async for day in db.timetable.find():
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
    try:
        return await handler(request)
    except Exception as e:
        return web.HTTPInternalServerError(text="""
Произошла непредвиденная ошибка на сервере, с этим уже разбираются.
Пока можете написать на hvdstudents@yandex.ru
""")


def make_app(loop):
    app = web.Application(
        loop=loop,
        middlewares=[
            auth_middleware,
            error_middleware,
        ]
    )
    app.router.add_get('/', index)
    # app.router.add_get('/static/{filename}', static)
    app.router.add_static('/static', 'static', show_index=True)

    app.router.add_get('/rest/get_timetable', rest.timetable)
    app.router.add_post('/rest/register', rest.register)
    app.router.add_post('/rest/unregister', rest.unregister)
    app.router.add_post('/rest/login', rest.login)
    app.router.add_get('/login', login)
    app.router.add_get('/heartbeat', heartbeat)
    app.router.add_get('/get_report', report)

    # app.router.add_get('/{name}', handle)

    aiohttp_jinja2.setup(app,
        loader=jinja2.FileSystemLoader('templates')
    )

    db = motor.AsyncIOMotorClient(S.mongo['url'])[S.mongo['db']]
    app['db'] = db
    app['running'] = True
    app['container'] = {'hash': 'asd'}

    async def db_auth(app):
        await app['db'].authenticate(S.mongo['username'], S.mongo['pwd'])

    async def run_db_hash_analyzer(app):
        asyncio.ensure_future(db_hash_analyzer(app))

    async def db_hash_analyzer(app):
        while app['running']:
            try:
                data = await app['db'].timetable.find().to_list(None)
                app['container']['hash'] = hashlib.md5(str(data).encode()).hexdigest()
            finally:
                await asyncio.sleep(1)

    app.on_startup.append(db_auth)
    app.on_startup.append(run_db_hash_analyzer)

    return app

web.run_app(make_app(asyncio.get_event_loop()), port=9000)