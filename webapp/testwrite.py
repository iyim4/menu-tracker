# testwrite.py
# test write to remote database

from flask import Flask, request, render_template
from datetime import datetime, timedelta
import pyodbc
import os

# get environment variables (for connecting to database)
DB_SERVER_NAME = os.getenv('DB_SERVER_NAME')
DB_NAME = os.getenv('DB_NAME')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_TABLE_NAME = os.getenv('DB_TABLE_NAME') # temporary. will implement date searches later.

# Connect to database
connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{DB_SERVER_NAME},1433;Database={DB_NAME};"\
    f"Uid={DB_USERNAME};Pwd={DB_PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
connection = pyodbc.connect(connection_string)
cursor = connection.cursor()

# create table
cursor.execute(f'''
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{DB_TABLE_NAME}' AND xtype='U')
    CREATE TABLE {DB_TABLE_NAME} (
        Recipe varchar(50),
        Date datetime,
        Mealtime int,
        Location int
    )
''')

date = datetime.today()
date = datetime(date.year, date.month, date.day)
instr = f"INSERT INTO {DB_TABLE_NAME} (Recipe, [Date], Mealtime, [Location]) VALUES (?, ?, ?, ?)"
cursor.execute(instr, 'Testrecipename', date, 0, 0) 
cursor.execute(instr, 'Testrecipename2', date, 1, 0) 
cursor.execute(instr, 'Testrecipename3', date, 0, 1) 

connection.close()