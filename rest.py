import asyncio
import datetime

from aiohttp import web
from bson import json_util, ObjectId
import json
from aiohttp_auth import auth

CRITICAL_TIMEDELTA = datetime.timedelta(days=-10, hours=13)

def dmps(obj):
    return json.dumps(obj, default=json_util.default)

async def timetable(request):
    return web.json_response(await request.app['db'].timetable.find().to_list(None), dumps=dmps)

async def register(request):
    db = request.app['db']

    try:
        data, user_id, user, day, period, idx, lab = await prepare_event(request)
    except web.HTTPError as e:
        return e

    for user_lab in user['labs'].values():
        if user_lab['day'] == day['day'] and user_lab['day'] == data['period']:
            return web.HTTPForbidden(text='у вас уже занят выбранный период')
        
    if lab['students_registered'] >= lab['quota']:
        return web.HTTPNotFound(text=f'в выбранной отработке не осталось свободных мест')

    await asyncio.gather(
        db.timetable.update_one({'_id': ObjectId(data['day-id'])}, {'$inc': {
            f'periods.{data["period"]}.labs.{idx}.students_registered': 1
        }}),
        db.users.update_one({'_id': int(user_id)}, {'$set': {
            f'labs.{data["lab-id"]}': {'day': day['day'], 'period': data['period'], 'critical_time': day['day'] + CRITICAL_TIMEDELTA}
        }}),
    )

    return {
        'user': int(user_id),
        'level': 'info',
        'event': 'registered',
        'entity': {
            'lab': data["lab-id"],
            'day': day['day'],
            'period': data['period'],
        },
        'timestamp': datetime.datetime.now(),
    }

async def prepare_event(request):
    data = await request.post()
    db = request.app['db']

    user_id = await auth.get_auth(request)
    if not user_id:
        raise web.HTTPForbidden(text='войдите в систему')
    user = request['user']
    if not user:
        raise web.HTTPNotFound(text='вы отсутствуете в системе')
    if user['group'] != data['group']:
        raise web.HTTPForbidden(text='не пытайтесь подделать данные')

    day = await db.timetable.find_one({'_id': ObjectId(data['day-id'])})
    if not day:
        raise web.HTTPNotFound(text='выбран несуществующий день')

    period = day['periods'].get(data['period'])
    if not period:
        raise web.HTTPNotFound(text='выбран несуществующий период')

    if user['group'] not in period['groups']:
        raise web.HTTPNotFound(text='выбранный день не доступен вашей группе')

    try:
        [(idx, lab,)] = [(i, lab) for i, lab in enumerate(period['labs']) if lab['_id'] == data['lab-id']]
    except Exception:
        raise web.HTTPNotFound(text=f'в выбранном дне не запланированы отработки {data["lab-id"]} л/р')
    return data, user_id, user, day, period, idx, lab


async def unregister(request):
    db = request.app['db']

    try:
        data, user_id, user, day, period, idx, lab = await prepare_event(request)
    except web.HTTPError as e:
        return e

    lab_id = lab['_id']
    if lab_id not in user['labs'].keys():
        return web.HTTPForbidden(text='вы не регистрировались на эту отработку')

    user_cmd = {'$unset': {
        f'labs.{lab_id}': 1
    }}
    if datetime.datetime.now() > user['labs'][lab_id]['critical_time']:
        user_cmd['$set'] = {
            f'blocks.{lab_id}': datetime.datetime(2017, 12, 23)
        }

    await asyncio.gather(
        db.timetable.update_one({'_id': ObjectId(data['day-id'])}, {'$inc': {
            f'periods.{data["period"]}.labs.{idx}.students_registered': -1
        }}),
        db.users.update_one({'_id': int(user_id)}, user_cmd),
    )

    return {
        'user': int(user_id),
        'level': 'info',
        'event': 'unregistered',
        'entity': {
            'lab': lab_id,
            'day': day['day'],
            'period': data['period'],
        },
        'timestamp': datetime.datetime.now(),
    }

async def login(request):
    data = await request.post()
    db = request.app['db']
    try:
        _id = int(data["id"])
        if await db.users.find({'_id': _id}).to_list(None):
            await auth.remember(request, data['id'])
            return web.HTTPFound('/')
    except:
        pass
    return web.Response(text="вы не зарегистрированы в системе")