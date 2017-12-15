from xml.etree import cElementTree as ET
import datetime
from glob import glob

WORKDAY, HOLIDAY = 'workday', 'holiday'
EXCEPTION_DATES = {}

ONE_DAY = datetime.timedelta(days=1)

DATE_FMT = "%Y.%m.%d"

def is_workday(tdate):
    try:
        tdate = tdate.date()
    except AttributeError:
        pass
    if tdate in EXCEPTION_DATES:
        return EXCEPTION_DATES[tdate] == WORKDAY
    else:
        return tdate.isoweekday() not in (6,  7)

def get_workdays_delta(tdate, n):
    while n > 0:
        tdate = tdate + ONE_DAY
        if not is_workday(tdate):
            continue
        n -=1
    return tdate

def load_exception():
    for filename in glob('calendar*.xml'):
        with open(filename, 'r') as fd:
            tree = ET.parse(fd)
            root = tree.getroot()
            year = root.attrib['year']
            for day in root.iter('day'):
                day_str = day.attrib['d']
                day_type = int(day.attrib['t'])
                if day_type not in (1, 2, 3):
                    raise Exception('wrong calendar')
                tdate = datetime.datetime.strptime(f'{year}.{day_str}', DATE_FMT).date()
                EXCEPTION_DATES[tdate] = WORKDAY if day_type in (2, 3) else HOLIDAY

load_exception()