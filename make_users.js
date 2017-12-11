db.users.drop();

db.users.insert({

    _id: NumberInt(123456),

    name: 'Иванов Иван Иванович',

    group: 'Э-15-15',

    labs: {

        '17': {'day': ISODate('2017-12-20'), 'period': 'first'}

    }

})