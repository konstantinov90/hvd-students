db.timetable.drop();

db.getCollection('timetable').insert({

    day: ISODate('2017-12-20'),

    periods: {

        first: {

            groups: [

                'Э-4-07',

                'Э-15-15'

            ],

            labs: [

                {

                    _id: '17',

                    students_registered: NumberInt(0),

                    quota: NumberInt(8)

                },

                {

                    _id: '20',

                    students_registered: NumberInt(0),

                    quota: NumberInt(8)

                }

            ]

        },

        second: {

            students_registered: NumberInt(0),

            quota: NumberInt(16),

            groups: [

                'Э-4-07',

                'Э-15-15'

            ],

            labs: [

                {

                    _id: '8',

                    students_registered: NumberInt(0),

                    quota: NumberInt(4)

                },

                {

                    _id: '1',

                    students_registered: NumberInt(8),

                    quota: NumberInt(8)

                }

            ]

        }

    }

});

db.getCollection('timetable').insert({

    day: ISODate('2017-12-25'),

    periods: {

        first: {

            students_registered: NumberInt(0),

            quota: NumberInt(8),

            groups: [

                'Э-10-18',

                'Э-15-15'

            ],

            labs: [

                {

                    _id: '17',

                    students_registered: NumberInt(0),

                    quota: NumberInt(8)

                }

            ]

        },

        second: {

            students_registered: NumberInt(0),

            quota: NumberInt(16),

            groups: [

                'Э-7-14'

            ],

            labs: [

                {

                    _id: '17',

                    students_registered: NumberInt(0),

                    quota: NumberInt(8)

                },

                {

                    _id: '20',

                    students_registered: NumberInt(0),

                    quota: NumberInt(8)

                }

            ]

        }

    }

});

db.getCollection('timetable').insert({

    day: ISODate('2017-12-26'),

    periods: {

        first: {

            students_registered: NumberInt(0),

            quota: NumberInt(8),

            groups: [

                'Э-10-18',

                'Э-15-15'

            ],

            labs: [

                {

                    _id: '20',

                    students_registered: NumberInt(0),

                    quota: NumberInt(8)

                }

            ]

        },

        second: {

            students_registered: NumberInt(0),

            quota: NumberInt(16),

            groups: [

                'Э-7-14'

            ],

            labs: [

                {

                    _id: '17',

                    students_registered: NumberInt(0),

                    quota: NumberInt(8)

                },

                {

                    _id: '20',

                    students_registered: NumberInt(0),

                    quota: NumberInt(8)

                }

            ]

        }

    }

})