# run_scraper.py
# runs webscraper to add data to database
# currently scrapes from all 3 dining halls up to CHECK_DAYS_AHEAD days in the future
# requires requests and BeautifulSoup4 (web scraping) and pyodbc (database connection) to be installed

import logging
import os
import sys
from datetime import datetime, timedelta
from scraper import scraper_main, get_logger

# import methods from searchdb: Add the parent directory to the system path to access it
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from searchdb import LOCATION_CODES, get_connection, get_table_name, is_valid_tname

# the number of days ahead from to scrape from
CHECK_DAYS_AHEAD = 17

# Set up logging
logger = get_logger()

# Get the date to begin searching from
date = datetime.today()
date = datetime(date.year, date.month, date.day)
start_date = date
logger.debug(f'Search starting from {start_date.date()} to {(date + timedelta(days=CHECK_DAYS_AHEAD)).date()}')

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
        logger.debug(f'CREATED NEW TABLE {table_name} as it was not found')
        # print(f'NOTICE run_scraper.py table {table_name} was not found, created new table')

    # add table to list of tables
    if tables == [] or tables[-1] != table_name:
        tables.append(table_name)

    # scrape from each dining hall location on this date
    for loc_num in range(1, 4):
        logger.debug(f'Scraping from {LOCATION_CODES[loc_num]}, {date.date()}')
        scraper_main(loc_num, date, table_name, cursor)
        pass

    # get next date and table_name
    date = date + timedelta(days=1)
    table_name = get_table_name(date)

# commit writes and close
connection.commit()
connection.close()

# log success
logger.info(f'Successfully scraped from {start_date.date()} to '\
            f'{(date - timedelta(days=1)).date()} and stored into tables {", ".join(tables)}')
