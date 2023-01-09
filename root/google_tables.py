import os
import time

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import sqlite3

import schedule

def update_tables():
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly',
              'https://www.googleapis.com/auth/drive']

    credentials = ServiceAccountCredentials.from_json_keyfile_name('google_key.json', scopes=scopes)

    sql_connect = sqlite3.connect('main.db', timeout=20)
    base = sql_connect.cursor()

    file = gspread.authorize(credentials)

    workbook = file.open("ProfPoint Бот")
    user_sheet = workbook.worksheet('Пользователи')
    log_sheet = workbook.worksheet('История')
    rows1 = base.execute("""SELECT * FROM users""").fetchall()
    rows2 = base.execute("""SELECT * FROM log""").fetchall()
    user_sheet.update(f'A2:AA{len(rows1) + 1}', rows1)
    log_sheet.update(f'A2:AA{len(rows2) + 1}', rows2)
    dbs_list = os.listdir('db')
    i = 2
    all_sheets = workbook.worksheets()
    for db in dbs_list:
        try:
            with sqlite3.connect(f'db/{db}', timeout=20) as company_db:
                company_rows = company_db.execute("""SELECT * FROM proverka""").fetchall()
                all_sheets[i].update(f'A2:AA{len(company_rows) + 1}', company_rows)
                company_rows = ()
                i += 1
        except:
            i += 1
        time.sleep(0.2)

schedule.every(15).minutes.do(update_tables)

while True:
    schedule.run_pending()
    time.sleep(5)


