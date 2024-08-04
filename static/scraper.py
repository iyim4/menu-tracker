# scraper.py
# Scrapes and stores recipes from a UT austin menu URL into database

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import requests
import pyodbc
from searchdb import MEALTIME_CODES, LOCATION_CODES

def scraper_main(location_num: int, date: datetime, table_name: str, cursor: pyodbc.Cursor):
    """Scrapes and stores recipes from a UT austin menu URL into database

    :location_num: of location to scrape from, must be 1, 2, or 3
    :date: to scrape from, recommended to be between 7 days ago and 14 days ahead
    :table_name: name of table in database
    :cursor: cursor to the database
    """

    # validate arguments
    if not is_valid_lnum(location_num):
        print(f'ERROR scraper.py location_num ({location_num}) is not valid. scraping cancelled from '\
              f'{LOCATION_CODES[location_num]}, {date.date()}')
        return
    elif not is_valid_tname(cursor, table_name):
        print(f'ERROR scraper.py {table_name} not found in database. scraping cancelled from '\
              f'{LOCATION_CODES[location_num]}, {date.date()}')
        return 
    elif not is_valid_date(date):
        print(f'NOTICE scraper.py date ({date.date()}) is not within recommended range, may not find data.')

    # write only if not already scraped
    if is_scraped(cursor, table_name, location_num, date):
        print(f'NOTICE scraper.py already scraped from {LOCATION_CODES[location_num]}, {date.date()}, '\
              f'into {table_name}. database was not updated.')
        return
    else:
        print(f'scraper.py begin scraping from {LOCATION_CODES[location_num]}, {date.date()}.')
    
    # scrape website
    html_content = get_html_content(location_num, date)

    # write only if there is data available
    if html_content.find(text='No Data Available'):
        print(f'NOTICE scraper.py No data found. scraping cancelled from '\
              f'{LOCATION_CODES[location_num]}, {date.date()}')
        return

    # write to database
    write(cursor, table_name, html_content, location_num, date)

    # print success message
    print(f'scraper.py successfully scraped from {LOCATION_CODES[location_num]}, {date.date()}')

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
    html_content = requests.get(source_url).text

    # Parse and return the HTML content
    return BeautifulSoup(html_content, 'html.parser')


def write(cursor: pyodbc.Cursor, table_name: str, html_content: BeautifulSoup, 
          location_num:int, date: datetime):
    """ Filters, formats, and writes html_content to file

    :cursor: cursor to execute queries
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

        # Write each recipe
        for recipe in recipe_list:
            instr = f"INSERT INTO {table_name} (Recipe, [Date], Mealtime, [Location]) VALUES (?, ?, ?, ?)"
            cursor.execute(instr, recipe.text.rstrip('\xa0'), date, mealtime, location_num) 

    # Print a success message
    print(f'scraper.py Recipes from {LOCATION_CODES[location_num]} on {date.date()} has '\
          f'been successfully written to table {table_name}')
    if len(menus) == 0:
        print('NOTICE scraper.py No recipes found, so new entries were made. THIS SHOULD NOT HAPPEN WITH NEW CHECK')

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
