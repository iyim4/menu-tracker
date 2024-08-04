# run_scraper.py
# runs webscraper to add data to database
# currently scrapes from all 3 dining halls up to CHECK_DAYS_AHEAD days in the future

from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to the system path to import methods from searchdb
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# import methods from other files
from searchdb import LOCATION_CODES, get_connection, get_table_name, is_valid_tname
from scraper import scraper_main

CHECK_DAYS_AHEAD = 40  # number of days ahead to check from date

# Get the date to begin searching from
date = datetime.today()
date = datetime(date.year, date.month-1, date.day+20)
start_date = date

# Connect to database
connection = get_connection()
cursor = connection.cursor()

# get first table
table_name = get_table_name(date)

# store tables written to in a list
tables = []

# scrape by location and date
for i in range(0, CHECK_DAYS_AHEAD + 1):
    # Create the table if it doesn't exist
    if not is_valid_tname(cursor, table_name):
        cursor.execute(f'''
            CREATE TABLE {table_name} (
                Recipe varchar(70),
                Date datetime,
                Mealtime int,
                Location int
            )
        ''')
        print(f'NOTICE run_scraper.py table {table_name} was not found, created new table')

    # add table to list of tables
    if tables == [] or tables[-1] != table_name:
        tables.append(table_name)

    # scrape from each dining hall location on this date
    for loc_num in range(1, 4):
        # print(f'run_scraper.py checking {LOCATION_CODES[loc_num]} on {date.date()}')
        scraper_main(loc_num, date, table_name, cursor)
        pass

    # get next date and table_name
    date = date + timedelta(days=1)
    table_name = get_table_name(date)

# commit writes and close
connection.commit()
connection.close()

# print sucess message
print(f'run_scraper.py successfully scraped from {start_date.date()} to {date.date()}',
      'and stored into tables', ', '.join(tables))
