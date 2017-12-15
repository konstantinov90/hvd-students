db.log.aggregate([
    {$group: {_id: '$user'}}
])