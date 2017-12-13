import datetime
import xlrd
import pymongo
import settings as S

def minimalist_xldate_as_datetime(xldate, datemode):
    # datemode: 0 for 1900-based, 1 for 1904-based
    return (
        datetime.datetime(1899, 12, 30)
        + datetime.timedelta(days=xldate + 1462 * datemode)
        )

FILENAME = 'c:\PYTHON\hvd-students\График отработок ЛР для Саши.xlsx'

def run():
    db = pymongo.MongoClient(S.mongo['url'])[S.mongo['db']]
    db.authenticate(S.mongo['username'], S.mongo['pwd'])
    db.timetable.drop()

    wb = xlrd.open_workbook(FILENAME)
    ws = wb.sheets()[0]
    for i in range(2, 22, 2):
        tdate_cell = ws.cell(0, i)
        tdate = minimalist_xldate_as_datetime(tdate_cell.value, 0)
        db.timetable.insert({'day': tdate, 'periods': {}})

    for j in range(2, 22):
        tdate_cell = ws.cell(0, j - j % 2)
        tdate = minimalist_xldate_as_datetime(tdate_cell.value, 0)
        period = 'first' if not j % 2 else 'second'
        for i in range(3, 13):
            if ws.cell(i, j).value.strip() != '+':
                continue
            group = ws.cell(i, 1).value.strip()
            print(group, tdate, period)
            db.timetable.update_one({'day': tdate}, { 
                '$addToSet': {
                    f'periods.{period}.groups': group
                }, "$set": {
                    f'periods.{period}.labs': []
                }
            })
        for i in range(16, 22):
            if not ws.cell(i,j).value:
                continue
            lab_id = str(int(ws.cell(i,j).value))
            quota = int(ws.cell(i, 22).value)
            print(tdate, period, lab_id, quota)
            db.timetable.update_one({'day': tdate}, { 
                "$push": {
                    f'periods.{period}.labs': {
                        "$each": [{"_id": lab_id, "students_registered": 0, "quota": quota, "order": int(lab_id)}],
                        "$sort": {"order": 1}
                    }
                }
            })
        # db.timetable.update_many({}, {"$set": {
        #     f'periods.{period}.labs._id': f'periods.{period}.labs._id'
        # }})


if __name__ == '__main__':
    run()