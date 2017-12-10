import asyncio

from aiohttp import web
from bson import json_util, ObjectId
import json
from aiohttp_auth import auth

def dmps(obj):
    return json.dumps(obj, default=json_util.default)

async def timetable(request):
    return web.json_response(await request.app['db'].timetable.find().to_list(None), dumps=dmps)

async def register(request):
    data = await request.post()
    db = request.app['db']

    user_id = await auth.get_auth(request)
    if not user_id:
        return web.HTTPForbidden(text='войдите в систему')
    user = await db.users.find_one({'_id': int(user_id)})
    if not user:
        return web.HTTPNotFound(text='вы отсутствуете в системе')
    if user['group'] != data['group']:
        return web.HTTPForbidden(text='не пытайтесь подделать данные')

    day = await db.timetable.find_one({'_id': ObjectId(data['day-id'])})

    if not day:
        return web.HTTPNotFound(text='выбран несуществующий день')

    for lab in user['labs'].values():
        if lab['day'] == day['day'] and lab['day'] == data['period']:
            return web.HTTPForbidden(text='у вас уже занят выбранный период')

    period = day['periods'][data['period']]
    if not period:
        return web.HTTPNotFound(text='выбран несуществующий период')
    if user['group'] not in period['groups']:
        return web.HTTPNotFound(text='выбранный день не доступен вашей группе')
    try:
        [(idx, lab,)] = [(i, lab) for i, lab in enumerate(period['labs']) if lab['_id'] == data['lab-id']]
    except Exception:
        return web.HTTPNotFound(text=f'в выбранном дне не запланированны отработки {data["lab-id"]} л/р')
    if lab['students_registered'] >= lab['quota']:
        return web.HTTPNotFound(text=f'в выбранной отработке не осталось свободных мест')

    await asyncio.gather(
        db.timetable.update_one({'_id': ObjectId(data['day-id'])}, {'$inc': {
            f'periods.{data["period"]}.labs.{idx}.students_registered': 1
        }}),
        db.users.update_one({'_id': int(user_id)}, {'$set': {
            f'labs.{data["lab-id"]}': {'day': day['day'], 'period': data['period']}
        }})
    )

    return web.Response(text="ok")

async def unregister(request):
    data = await request.post()
    db = request.app['db']

    user_id = await auth.get_auth(request)
    if not user_id:
        return web.HTTPForbidden(text='войдите в систему')
    user = await db.users.find_one({'_id': int(user_id)})
    if not user:
        return web.HTTPNotFound(text='вы отсутствуете в системе')
    if user['group'] != data['group']:
        return web.HTTPForbidden(text='не пытайтесь подделать данные')

    day = await db.timetable.find_one({'_id': ObjectId(data['day-id'])})

    if not day:
        return web.HTTPNotFound(text='выбран несуществующий день')
    period = day['periods'][data['period']]
    if not period:
        return web.HTTPNotFound(text='выбран несуществующий период')
    if user['group'] not in period['groups']:
        return web.HTTPNotFound(text='выбранный день не доступен вашей группе')
    try:
        [(idx, lab,)] = [(i, lab) for i, lab in enumerate(period['labs']) if lab['_id'] == data['lab-id']]
    except Exception:
        return web.HTTPNotFound(text=f'в выбранном дне не запланированны отработки {data["lab-id"]} л/р')

    await asyncio.gather(
        db.timetable.update_one({'_id': ObjectId(data['day-id'])}, {'$inc': {
            f'periods.{data["period"]}.labs.{idx}.students_registered': -1
        }}),
        db.users.update_one({'_id': int(user_id)}, {'$unset': {
            f'labs.{data["lab-id"]}': 1
        }})
    )

    return web.Response(text="ok")

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