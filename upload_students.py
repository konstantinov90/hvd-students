import datetime
import xlrd
import pymongo

def minimalist_xldate_as_datetime(xldate, datemode):
    # datemode: 0 for 1900-based, 1 for 1904-based
    return (
        datetime.datetime(1899, 12, 30)
        + datetime.timedelta(days=xldate + 1462 * datemode)
        )

FILENAME = 'f:\PYTHON\hvd-students\список студентов.xlsx'

def run():
    db = pymongo.MongoClient('ds044787.mlab.com:44787').students
    db.authenticate('app','studentsapp')
    db.users.drop()

    wb = xlrd.open_workbook(FILENAME)
    ws = wb.sheets()[0]
    for i in range(198):
        name = ws.cell(i, 0).value.strip()
        user_id = int(ws.cell(i, 1).value)
        group = ws.cell(i, 2).value.strip()
        print(user_id, name, group)
        db.users.insert({'_id': user_id, 'labs': {}, 'group': group, 'name': name})


if __name__ == '__main__':
    run()