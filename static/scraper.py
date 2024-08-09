# scraper.py
# Scrapes and stores recipes from a UT austin menu URL into database
# requires requests and BeautifulSoup4 (web scraping) and pyodbc (database connection) to be installed

import logging
import os
import sys
from datetime import datetime, timedelta
import pyodbc
from requests import get
from bs4 import BeautifulSoup

# import methods from searchdb: Add the parent directory to the system path to access it
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from searchdb import MEALTIME_CODES, LOCATION_CODES

def get_logger(): 
    """ returns logger that this file writes to """
    LOG_NAME = 'scraper.log'
    LOG_LEVEL = logging.INFO
    current_dir = os.path.dirname(__file__)
    log_path = os.path.join(os.path.dirname(__file__), LOG_NAME)
    logging.basicConfig(level=LOG_LEVEL, filename=log_path, filemode='w',
                        format="%(asctime)s [%(levelname)s] %(filename)s: %(message)s")
    return logging.getLogger(LOG_NAME)

def scraper_main(location_num: int, date: datetime, table_name: str, cursor: pyodbc.Cursor):
    """Scrapes and stores recipes from a UT austin menu URL into database

    :location_num: of location to scrape from, must be 1, 2, or 3
    :date: to scrape from, recommended to be between 7 days ago and 14 days ahead
    :table_name: name of table in database
    :cursor: cursor to the database, executes writes.  DOES NOT COMMIT WRITE
    """

    logger = get_logger()
    logger.debug(f'Attempting to scrape with location {location_num}, date {date.date()}, and table {table_name}')

    # validate arguments
    if not is_valid_lnum(location_num):
        logger.warning(f'SCRAPE CANCELLED from {LOCATION_CODES[location_num]}, {date.date()}. '\
                       f'Location_num ({location_num}) is not valid.')
        return
    elif not is_valid_tname(cursor, table_name):
        logger.warning(f'SCRAPE CANCELLED from {LOCATION_CODES[location_num]}, {date.date()}. '\
                       f'Table ({table_name}) not found in database.')
        return 
    elif not is_valid_date(date):
        logger.debug(f'Date ({date.date()}) is not within recommended range, may not find data.')

    # write only if not already scraped
    if is_scraped(cursor, table_name, location_num, date):
        logger.debug(f'SCRAPE CANCELLED from {LOCATION_CODES[location_num]}, {date.date()}. '\
              f'Already scraped into {table_name}.')
        return
    else:
        logger.debug(f'Begin scraping from {LOCATION_CODES[location_num]}, {date.date()}.')
    
    # scrape website
    html_content = get_html_content(location_num, date)

    # write only if there is data available
    if html_content.find(text='No Data Available'):
        logger.debug(f'SCRAPE CANCELLED from {LOCATION_CODES[location_num]}, {date.date()}. '\
                       f'No recipes found on page')
        return

    # write to database
    write(cursor, table_name, html_content, location_num, date)
    logger.debug('no writes occurred')

    # print success message
    logger.info(f'Successfully scraped and cursor-wrote from {LOCATION_CODES[location_num]}, {date.date()}')

def is_valid_date(date: datetime):
    """ Returns true if date is within a valid range, between 7 days ago and 14 days ahead of today """
    # check for dates because the URL may not work otherwise - blank search result
    return not (datetime.today() - timedelta(days=7) > date > datetime.today() + timedelta(days=14))

def is_valid_lnum(location_num: int):
    """ Returns true if location_num is a valid location code, false otherwise """
    # valid location codes are 1, 2, 3
    return location_num in [1, 2, 3]

def is_valid_tname(cursor: pyodbc.Cursor, table_name: str):
    """ Returns true if table_name is a valid table name (present in database), false otherwise """
    return cursor.tables(table=table_name, tableType='TABLE').fetchone() is not None

def get_html_content(location_num: int, date: datetime):
    """Get HTML content

    :location_num: to scrape from, should be 1, 2, or 3
    :date: to scrape from, recommended to be between 7 days ago or 14 days ahead
    """

    # for converting database codes to url codes
    LOCATION_CODES_URL = ['ERROR', 3, 12, 1]
    LOCATION_STRINGS_URL = ['ERROR', 'Kins+Dining', 'J2+Dining', 'Jester+City+Limits+(JCL)']
    
    # build url
    source_url = (
        'https://hf-foodpro.austin.utexas.edu/foodpro/shortmenu.aspx?sName=University+Housing+and+Dining'
        f'&locationNum={LOCATION_CODES_URL[location_num]}&locationName={LOCATION_STRINGS_URL[location_num]}'
        '&naFlag=1&WeeksMenus=This+Week%27s+Menus&myaction=read'
        f'&dtdate={date.month}%2f{date.day}%2f{date.year}'
    )

    # Get HTML from website
    html_content = get(source_url).text

    # Parse and return the HTML content
    return BeautifulSoup(html_content, 'html.parser')


def write(cursor: pyodbc.Cursor, table_name: str, html_content: BeautifulSoup, 
          location_num:int, date: datetime):
    """ Filters, formats, and writes html_content to file

    :cursor: cursor to execute queries, DOES NOT COMMIT WRITES
    :table_name: name of table in database to write to
    :html_content: parsed html content
    :location_num: of recipes in html_content, should be 1, 2, or 3
    :date: of recipes in html_content
    """

    # Find each menu (mealtime and recipes)
    menus = html_content.find_all('table', {'border': '0', 'width': '100%', 'height': '100%',
                                     'cellpadding': '0', 'cellspacing': '0'})

    # Find each mealtime and recipes then write it
    for menu in menus:
        # Find and encode mealtime
        mealtime = MEALTIME_CODES.index(menu.find('div', class_='shortmenumeals').text)

        # Find all recipes in recipe_table
        recipe_list = menu.find('tr').find_next_sibling().find_all('div', class_='shortmenurecipes')

        # Remove duplicates
        recipe_list = set(recipe_list)

        # Write each recipe
        for recipe in recipe_list:
            instr = f"INSERT INTO {table_name} (Recipe, [Date], Mealtime, [Location]) VALUES (?, ?, ?, ?)"
            cursor.execute(instr, recipe.text.rstrip('\xa0'), date, mealtime, location_num) 

    # Log a success message
    logger = get_logger()
    logger.debug(f'Recipes from {LOCATION_CODES[location_num]} on {date.date()} has '\
          f'been successfully written to table {table_name}')

def is_scraped(cursor: pyodbc.Cursor, table_name: str, location_num: int, date: datetime):
    """Checks if this day and location have already been scraped into database

    :cursor: cursor to database
    :table_name: name of table in database to read from
    :location_num: to check, should be 1, 2, or 3
    :date: to check
    """
    
    # Attempt to find matches in database
    date_string = date.date().strftime('%Y-%m-%d')  # convert date to string in 'YYYY-MM-DD' format
    instr = f"SELECT TOP 1 * FROM {table_name} WHERE [Date]='{date_string}' AND [Location]={location_num}"
    cursor.execute(instr)

    # Convert to boolean and return
    return len(cursor.fetchall()) != 0  
