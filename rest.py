import asyncio
import datetime
import os
import hashlib

from aiohttp import web
from bson import json_util, ObjectId
import json
from aiohttp_auth import auth

def dmps(obj):
    return json.dumps(obj, default=json_util.default)

async def sign_up(request):
    if request['user']:
        return web.HTTPFound('/')
    
    db = request.app['db']
    data = await request.post()
    if data['password'] != data['password2']:
        return web.HTTPFound(f'/sign-up?id={data["id"]}&msg=unequal-pwds')
    if not data['password']:
        return web.HTTPFound(f'/sign-up?id={data["id"]}')
    _id = int(data['id'])
    user = await db.users.find_one({'_id': _id})
    if not user:
        return web.HTTPForbidden(text="вы не зарегистрированы в системе")
    if 'pwd' in user:
        return web.HTTPFound('/')
    pwd = data['password']
    salt = os.urandom(16)
    enc_pwd = hashlib.md5(salt + pwd.encode()).hexdigest()
    await db.users.update_one({'_id': _id}, {
        '$set': {'pwd': enc_pwd, 'salt': salt}
    })
    return await login(request, pwd)

async def login(request, _pwd=None):
    data = await request.post()
    db = request.app['db']
    if _pwd:
        pwd = _pwd
    else:
        pwd = data['password']
    _id = int(data["id"])
    user = await db.users.find_one({'_id': _id})
    if not user:
        return web.HTTPForbidden(text="вы не зарегистрированы в системе")
    if not user.get('allowed'):
        return web.HTTPForbidden(text="Вы выполнили все лабораторные работы и запись вам не требуется")
    if 'pwd' not in user:
        return web.HTTPFound(f'/sign-up?id={_id}')
    if hashlib.md5(user['salt'] + pwd.encode()).hexdigest() == user['pwd']:
        await auth.remember(request, data['id'])
        return web.HTTPFound('/')
    return web.HTTPFound('/login?msg=wrong-pwd')


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
    
    if datetime.datetime.now() >= period['availible_until']:
        return web.HTTPNotFound(text='регистрация закрыта')

    await asyncio.gather(
        db.timetable.update_one({'_id': ObjectId(data['day-id'])}, {'$inc': {
            f'periods.{data["period"]}.labs.{idx}.students_registered': 1
        }}),
        db.users.update_one({'_id': user_id}, {'$set': {
            f'labs.{data["lab-id"]}': {'day': day['day'], 'period': data['period']}
        }}),
    )

    return {
        'user': user_id,
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

    # if user['group'] not in period['groups']:
    #     raise web.HTTPNotFound(text='выбранный день не доступен вашей группе')

    try:
        [(idx, lab,)] = [(i, lab) for i, lab in enumerate(period['labs']) if lab['_id'] == data['lab-id'] and user['group'] in lab['groups']]
    except Exception:
        raise web.HTTPNotFound(text=f'в выбранном дне не запланированы отработки {data["lab-id"]} л/р')
    return data, int(user_id), user, day, period, idx, lab


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
    if datetime.datetime.now() > day['critical_time']:
        user_cmd['$set'] = {
            f'blocks.{lab_id}': day['block_until']
        }

    await asyncio.gather(
        db.timetable.update_one({'_id': ObjectId(data['day-id'])}, {'$inc': {
            f'periods.{data["period"]}.labs.{idx}.students_registered': -1
        }}),
        db.users.update_one({'_id': user_id}, user_cmd),
    )

    return {
        'user': user_id,
        'level': 'info',
        'event': 'unregistered',
        'entity': {
            'lab': lab_id,
            'day': day['day'],
            'period': data['period'],
        },
        'timestamp': datetime.datetime.now(),
    }
