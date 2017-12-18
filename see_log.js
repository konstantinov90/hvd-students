var cursor = db.log.aggregate([
    {$match: {event: {$ne: null}}}
   ,{$lookup: {
       from: 'users',
       localField: 'user',
       foreignField: '_id',
       as: 'name'
    }}
   ,{$unwind: '$name'}
   ,{$project: {user: '$user', event: '$event', timestamp: '$timestamp',
                name: '$name.name', lab: '$entity.lab',
                labDate: {$concat: [
                    {$dateToString:{format:"%Y-%m-%d",date:'$entity.day'}}, ' ', '$entity.period'
                ]}
    }}
   ,{$sort: {timestamp: -1}}
])
while (cursor.hasNext()) {
   print(cursor.next());
}