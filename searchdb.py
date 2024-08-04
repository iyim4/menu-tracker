# searchdb.py
# provides methods to search database for availability of foods from UT Austin dining halls
# assumes connection details in environment variables

from datetime import datetime, timedelta
from enum import Enum
import pyodbc
import os

# mapping from database codes to strings
MEALTIME_CODES = ['ERROR', 'Breakfast', 'Lunch', 'Dinner']
LOCATION_CODES = ['ERROR', 'Kins', 'J2', 'JCL']

# Meal filters are used to filter food search results
# Filters are stored as a string of numbers. Each digit is used to determine
# a specific filter setting at the index corresponding to the MFilters enumeration
DEFAULT_MFILTER = '0111111'
class MFilters(Enum):
    NUM_FILTERS = 7
    # position of filter on filters string
    TIME = 0
    BREAKFAST = 1
    LUNCH = 2
    DINNER = 3
    KINS = 4
    J2 = 5
    JCL = 6
    # Time filter codes
    TIME_SHORT = 0
    TIME_FUTURE = 1
    TIME_ALL = 2
    TIME_SHORT_LIMIT = 3 # the number of days TIME_SHORT displays

def get_connection():
    """ gets connection to database from environment variables """
    
    # get environment variables (for connecting to database)
    DB_SERVER_NAME = os.getenv('DB_SERVER_NAME')
    DB_NAME = os.getenv('DB_NAME')
    DB_USERNAME = os.getenv('DB_USERNAME')
    DB_PASSWORD = os.getenv('DB_PASSWORD')

    # Connect to database
    connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{DB_SERVER_NAME},1433;Database={DB_NAME};"\
    f"Uid={DB_USERNAME};Pwd={DB_PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    return pyodbc.connect(connection_string)

def get_filtered_query(filters: str, food_name: str, exact_match: bool, cursor: pyodbc.Cursor):
    """ returns SQL query string for database using filters 

    :param filters: string determining selection filters. assume already validated.
    :param food_name: name of food to search
    :param exact_match: determines whether to search for exact matches to food_name
    :param table_names: used for date filters
    """
    
    # convert to list
    filters = list(filters[:MFilters.NUM_FILTERS.value])

    # handle special char ' (SQL syntax)
    if "'" in food_name:
        food_name = food_name.replace("'","''") 

    # determine whether to search for exact matches to food_name
    recipe_select = f"Recipe='{food_name}'" if exact_match else f"(Recipe LIKE '% {food_name}%' OR Recipe LIKE '{food_name}%')" 

    # order clause - displays search results in order by these column values
    order = ' ORDER BY Recipe, [Date], Mealtime'

    # Start building where clause (filters)
    where = [recipe_select]

    # Mealtime Filters
    mealtime_filters=[]
    if not ('1' == filters[MFilters.BREAKFAST.value] == filters[MFilters.LUNCH.value] == filters[MFilters.DINNER.value]):
        if filters[MFilters.BREAKFAST.value] == '1':
            mealtime_filters.append(f'Mealtime=1')
        if filters[MFilters.LUNCH.value] == '1':
            mealtime_filters.append(f'Mealtime=2')   
        if filters[MFilters.DINNER.value] == '1':
            mealtime_filters.append(f'Mealtime=3')
        if mealtime_filters != []:
            mealtime_filters = f'({" OR ".join(mealtime_filters)})'
            where.append(mealtime_filters)
    # else, search all mealtimes

    # Location filters
    loc_filters = []
    if not ('1' == filters[MFilters.KINS.value] == filters[MFilters.J2.value] == filters[MFilters.JCL.value]):
        if filters[MFilters.KINS.value] == '1':
            loc_filters.append(f'Location=1')
        if filters[MFilters.J2.value] == '1':
            loc_filters.append(f'Location=2')
        if filters[MFilters.JCL.value] == '1':
            loc_filters.append(f'Location=3')
        if loc_filters != []:
            loc_filters = f'({" OR ".join(loc_filters)})'
            where.append(loc_filters)
    # else, search all locations
    
    # Add time filters and return
    today = datetime.today()
    if filters[MFilters.TIME.value] == f'{MFilters.TIME_SHORT.value}':
        # searches to up to MFilters.TIME_SHORT_LIMIT - 1 days ahead
        start_date = today
        end_date = (today + timedelta(days=MFilters.TIME_SHORT_LIMIT.value - 1))
        if start_date.month == end_date.month:
            # both dates are in same month
            start_date = start_date.strftime("%m/%d/%Y")
            end_date = end_date.strftime("%m/%d/%Y")
            where.append(f"([Date] BETWEEN '{start_date}' AND '{end_date}')")
            return f'SELECT * from {get_table_name(today)} WHERE ' + ' AND '.join(where) + order
        else:
            # end_date is in another month and thus table. join tables
            start_date_str = start_date.strftime("%m/%d/%Y")
            where.append(f"([Date] >= '{start_date_str})'")
            table1 = f'SELECT * from {get_table_name(start_date)} WHERE' + ' AND '.join(where)
            where.pop() # remove previous date filter
            start_date = start_date.strftime("%m/%d/%Y")
            end_date = end_date.strftime("%m/%d/%Y")
            where.append(f"([Date] BETWEEN '{start_date}' AND '{end_date}')")
            table2 = f'SELECT * from {get_table_name(end_date)} WHERE' + ' AND '.join(where)
            # Union tables and return
            return f'{table1} UNION {table2} {order}'
        
    elif filters[MFilters.TIME.value] == f'{MFilters.TIME_FUTURE.value}':
        # searches everything after start date
        start_date = today
        today_str = today.strftime("%m/%d/%Y")
        where.append(f"([Date] >= '{today_str}')")
        table1 = f'SELECT * from {get_table_name(today)} WHERE ' + ' AND '.join(where)

        # check there is data for next month
        month = start_date.month + 1 if start_date.month != 12 else 1
        year = start_date.year if month != 1 else start_date.year + 1
        next_month = datetime(year, month, 1)
        next_tname = get_table_name(next_month)
        if is_valid_tname(cursor, next_tname):
            # Union next month's table
            where.pop() # remove previous date filter
            table2 = f'SELECT * from {next_tname} WHERE ' + ' AND '.join(where)
            return f'{table1} UNION {table2} {order}'
        else:
            # no data for next month
            return f'{table1} {order}'
    
    else:
        # searches all time
        today = datetime.today()
        start_date = datetime(2024, 7, 1) # database won't contain any data before july 2024
        end_date = datetime(today.year, today.month, 1)
        temp_date = start_date

        # build list of tables to search
        tables = []

        # add past tables
        while not(temp_date.year == end_date.year and temp_date.month == end_date.month):
            tables.append(get_table_name(temp_date))
            month = temp_date.month + 1 if temp_date.month != 12 else 1
            year = temp_date.year if month != 1 else temp_date.year + 1
            temp_date = datetime(year, month, 1)

        # add this month's table
        tables.append(get_table_name(temp_date))

        # add next month's table if available
        month = end_date.month + 1 if end_date.month != 12 else 1
        year = end_date.year if month != 1 else end_date.year + 1
        next_month = datetime(year, month, 1)
        next_tname = get_table_name(next_month)
        if is_valid_tname(cursor, next_tname):
            tables.append(next_tname)

        # combine query elements to form full query
        where = ' AND '.join(where)
        query = [f'SELECT * from {table} WHERE {where}' for table in tables]
        return ' UNION '.join(query) + order

def get_table_name(date: datetime):
    """ returns table name in database for a date """
    # table names in format (prefix)_(year)_(month)
    DB_TABLE_PREFIX = os.getenv('DB_TABLE_PREFIX')
    return f'{DB_TABLE_PREFIX}_{date.year}_{date.month}'

def is_valid_tname(cursor: pyodbc.Cursor, table_name: str):
    """Returns true if table_name is a valid table name (present in database), false otherwise"""
    return cursor.tables(table=table_name, tableType='TABLE').fetchone() is not None

def load_menu_home(food_name: str, filters: str): 
    """ load all filtered search results for food from database in HOME PAGE format 

    :param food_name: name of food to search
    :param filters: string representing filter settings
    """
    # validate filters
    filters = validate_filters(filters, False)
    
    # Connect to database
    connection = get_connection()
    cursor = connection.cursor()

    # Get and execute the SQL query
    query = get_filtered_query(filters, food_name, False, cursor)
    print(f'load_menu_home searching for {food_name} with filters {filters} and query {query}')
    cursor.execute(query)

    # Fetch all rows
    rows = cursor.fetchall()

    # Extract data and store into a list, HOME PAGE FORMAT
    loaded_menu = []
    today = datetime.today()
    today = datetime(today.year, today.month, today.day)
    tomorrow = today + timedelta(days=1)
    for row in rows:
        date = row.Date
        date = 'Today' if date == today else ('Tomorrow' if date == tomorrow else f'{date.strftime("%A")}')
        loaded_menu.append([row.Recipe, date, MEALTIME_CODES[row.Mealtime], LOCATION_CODES[row.Location]])

    # Close the connection
    connection.close()
    print('load_menu_home completed sucessfully')
    
    return loaded_menu

def load_menu_details(food_name, filters):
    """ load filtered details for single food from database in DETAILS PAGE format 

    :param food_name: name of food to search
    :param filters: string representing filter settings
    """
    # validate filters
    filters = validate_filters(filters, True)

    # Connect to database
    connection = get_connection()
    cursor = connection.cursor()

    # Get and execute the SQL query
    query = get_filtered_query(filters, food_name, True, cursor)
    print(f'load_menu_details searching for {food_name} with filters {filters} and query {query}')
    cursor.execute(query)

    # Fetch all rows
    rows = cursor.fetchall()

    # Extract data and store into a list, DETAILS PAGE FORMAT
    loaded_details = []
    for row in rows:
        date = row.Date.strftime("%d %B '%y").lstrip('0')
        loaded_details.append([row.Recipe, date, MEALTIME_CODES[row.Mealtime], LOCATION_CODES[row.Location]])

    # Close the connection
    connection.close()
    print('load_menu_details completed sucessfully')
    
    return loaded_details

def validate_filters(filters_str: str, is_details_page: bool):
    """ checks that filters contains valid values, and returns corrected value otherwise 
    
    :param filters_str: the filter string to check
    :param is_details_page: if current route is /details
    """

    # special case if empty
    if filters_str == '':
        return DEFAULT_MFILTER
    
    # convert to list
    filters = list(filters_str[:MFilters.NUM_FILTERS.value])

    # add filters if necessary (assume included)
    while len(filters) < MFilters.NUM_FILTERS.value:
        filters.append('1')

    # check each digit is 0 or 1, or 2 for TIME
    for index in range(MFilters.NUM_FILTERS.value):
        digit = f'{filters[index]}'
        if digit != '0' and digit != '1':
            if not(is_details_page and index == MFilters.TIME.value and digit == '2'):
                filters[index] = '1'

    # return as string
    return ''.join(filters)