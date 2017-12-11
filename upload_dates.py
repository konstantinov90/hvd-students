import datetime
import xlrd
import pymongo

def minimalist_xldate_as_datetime(xldate, datemode):
    # datemode: 0 for 1900-based, 1 for 1904-based
    return (
        datetime.datetime(1899, 12, 30)
        + datetime.timedelta(days=xldate + 1462 * datemode)
        )

FILENAME = 'f:\PYTHON\hvd-students\График отработок ЛР.XLSX'

def run():
    db = pymongo.MongoClient('ds044787.mlab.com:44787').students
    db.authenticate('app','studentsapp')
    db.timetable.drop()

    wb = xlrd.open_workbook(FILENAME)
    ws = wb.sheets()[0]
    for i in range(2, 22, 2):
        tdate_cell = ws.cell(0, i)
        tdate = minimalist_xldate_as_datetime(tdate_cell.value, 0)
        db.timetable.insert({'day': tdate, 'periods': {}})

    for i in range(3, 13):
        for j in range(2, 22):
            if ws.cell(i, j).value.strip() != '+':
                continue
            group = ws.cell(i, 1).value.strip()
            tdate_cell = ws.cell(0, j - j % 2)
            tdate = minimalist_xldate_as_datetime(tdate_cell.value, 0)
            period = 'first' if not j % 2 else 'second'
            print(group, tdate, period)
            db.timetable.update_one({'day': tdate}, { 
                '$addToSet': {
                    f'periods.{period}.groups': group
                }, "$set": {
                    f'periods.{period}.labs': []
                }
            })


if __name__ == '__main__':
    run()