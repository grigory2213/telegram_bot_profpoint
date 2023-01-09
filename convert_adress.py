import sqlite3

import pandas as pd

pd.options.mode.chained_assignment = None
#
df_adress = pd.read_csv('subway.csv', index_col=0)
#
# df_adress = df_adress.rename(
#     columns={"ID": "unique_id", "Область": "region", "Город": "city", "Адрес": "adress", "Latitude": "latitude",
#              "Longitude": "longitude", "Тип ТТ": "building", "Оплата": "payment", "Дата": "open_date", "ТП": "done"})
conn = sqlite3.connect('db/subway.db', timeout=20)
df_adress['done'].fillna(0, inplace=True)
df_adress_done = df_adress.loc[df_adress['done'] != 0]
df_adress_done['done'] = 1
df_adress = pd.concat([df_adress, df_adress_done])
# print(df_adress)
df_adress_done = df_adress.loc[df_adress['done'] != 0]
df_adress_done['done'] = 1
df_adress_not_done = df_adress.loc[df_adress['done'] == 0]
df_adress = pd.concat([df_adress_done, df_adress_not_done])
# c = conn.cursor()
df_adress.to_sql('adress', conn, if_exists='append')
# users = c.execute("""SELECT * FROM users""").fetchall()
#
# print(users)