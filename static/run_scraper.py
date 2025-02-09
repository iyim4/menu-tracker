# run_scraper.py
# runs webscraper to add data to database
# currently scrapes from all 3 dining halls up to CHECK_DAYS_AHEAD days in the future
# requires requests and BeautifulSoup4 (web scraping) and pyodbc (database connection) to be installed

import os
import sys
from datetime import datetime, timedelta
import pyodbc 
from scraper import scraper_main, get_logger
from db_connection_info import CONNECTION_INFO # file ON MY COMPUTER storing login credentials
from predict_future_date import make_predictions
from searchdb import download_database_csv, ENTIRE_DATABASE_CSV_FILENAME

# import methods from searchdb: Add the parent directory to the system path to access it
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from searchdb import LOCATION_CODES

# the date to start scraping from
START_DATE = datetime.today()
# the number of days ahead from to scrape from
CHECK_DAYS_AHEAD = 11

# define helper methods
def get_table_name(date: datetime):
    """ returns table name in database for a date """
    return f'{CONNECTION_INFO.DB_TABLE_PREFIX}_{date.year}_{date.month}'

def is_valid_tname(cursor: pyodbc.Cursor, table_name: str):
    """ Returns true if table_name is a valid table name (present in cursor's database), false otherwise """
    return cursor.tables(table=table_name, tableType='TABLE').fetchone() is not None

LOCATION_CODES_URL = ['ERROR', '03', '12', '12(a)']
LOCATION_STRINGS_URL = ['ERROR', 'Kins+Dining', 'J2+Dining', 'Jester+City+Limits+(JCL)']
def get_url(location_num: int, date: datetime):
    """ returns url for dining hall at location and date """
    return (
        'https://hf-foodpro.austin.utexas.edu/foodpro/shortmenu.aspx?sName=University+Housing+and+Dining'
        f'&locationNum={LOCATION_CODES_URL[location_num]}&locationName={LOCATION_STRINGS_URL[location_num]}'
        '&naFlag=1&WeeksMenus=This+Week%27s+Menus&myaction=read'
        f'&dtdate={date.month}%2f{date.day}%2f{date.year}'
    )

# Log range
logger = get_logger()
logger.debug(f'Search starting from {START_DATE.date()} to {(START_DATE + timedelta(days=CHECK_DAYS_AHEAD)).date()}')

# Connect to database
connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{CONNECTION_INFO.DB_SERVER_NAME},1433;Database={CONNECTION_INFO.DB_NAME};"\
f"Uid={CONNECTION_INFO.DB_USERNAME};Pwd={CONNECTION_INFO.DB_PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
connection = pyodbc.connect(connection_string)
cursor = connection.cursor()

# get first table
date = datetime(START_DATE.year, START_DATE.month, START_DATE.day)
table_name = get_table_name(date)

# store tables written to in a list
tables = []

# scrape by location and date
for i in range(0, CHECK_DAYS_AHEAD + 1):
    # Create the table if it doesn't exist
    if not is_valid_tname(cursor, table_name):
        cursor.execute(f'''
            CREATE TABLE {table_name} (
                Recipe varchar(65),
                Date datetime,
                Mealtime int,
                Location int
            )
        ''')
        logger.debug(f'CREATED NEW TABLE {table_name} as it was not found')

    # add table to list of tables
    if tables == [] or tables[-1] != table_name:
        tables.append(table_name)

    # scrape from each dining hall location on this date
    for loc_num in range(1, 4):
        logger.debug(f'Scraping from {LOCATION_CODES[loc_num]}, {date.date()}')
        url = get_url(loc_num, date)
        scraper_main(url, loc_num, date, table_name, cursor)

    # get next date and table_name
    date += timedelta(days=1)
    table_name = get_table_name(date)

# commit writes
connection.commit()
logger.debug(f"Done writing data")

# Convert Database into CSV for training models
# download_database_csv(cursor)

# Re-train models with new data and save results into database
make_predictions(cursor, ENTIRE_DATABASE_CSV_FILENAME)

# commit writes
connection.commit()
logger.debug(f"Done predicting data and saving to database")

# close the connection
connection.close()

# log success
logger.info(f'Successfully scraped from {START_DATE.date()} to '\
            f'{(date - timedelta(days=1)).date()} and stored into tables {", ".join(tables)}')
