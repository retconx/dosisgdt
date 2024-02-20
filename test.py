import datetime
heute = datetime.date.today()
datum1 = datetime.date(2024,2,13)
datum2 = datetime.date(2024,2,18)
past = (heute - datum1).days
tage = (datum2 - datum1).days + 1 - past
print(tage)