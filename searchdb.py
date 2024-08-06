# searchdb.py
# provides methods to search database for availability of foods from UT Austin dining halls
# assumes connection details in environment variables
# TODO change print statements to logging statements

from datetime import datetime, timedelta
from enum import Enum
import pyodbc
import os

# mapping from database codes to strings
MEALTIME_CODES = ['ERROR', 'Breakfast', 'Lunch', 'Dinner']
LOCATION_CODES = ['ERROR', 'Kins', 'J2', 'JCL']

class MFilters(Enum):
    """ Meal filters are used to filter food search results.
    
    Filters are stored as a string of numbers. Each digit is used to determine
    a specific filter setting at the index corresponding to the MFilters enumeration.
    0 means off/exclude and 1 means on/include an option in the search result. 
    """

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
    TIME_SHORT_LIMIT = 10 # the number of days TIME_SHORT displays

    # default filter string. time is off and everything else is on
    def get_default_filter():
        return '0111111'

def load_menu_home(food_name: str, filters: str): 
    """ load all filtered search results for food from database, formatted for the home page

    :param food_name: name of food to search
    :param filters: string representing filter settings
    """

    # validate filters
    filters = validate_filters(filters, False)
    
    # Connect to database
    connection = get_connection()
    cursor = connection.cursor()

    # Get the SQL query
    query = get_filtered_query(filters, food_name, False, cursor)

    # Execute query
    print(f'load_menu_home searching for {food_name} with filters {filters} and query {query}')
    cursor.execute(query)

    # Fetch results of query
    rows = cursor.fetchall()

    # Extract data and store into a list, in the home page format
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

def load_menu_details(food_name: str, filters: str):
    """ load filtered details for single food from database, formatted for the details page

    :param food_name: name of food to search
    :param filters: string representing filter settings
    """

    # validate filters
    filters = validate_filters(filters, True)

    # Connect to database
    connection = get_connection()
    cursor = connection.cursor()

    # Get the SQL query
    query = get_filtered_query(filters, food_name, False, cursor)

    # Execute query
    print(f'load_menu_details searching for {food_name} with filters {filters} and query {query}')
    cursor.execute(query)

    # Fetch results of query
    rows = cursor.fetchall()

    # Extract data and store into a list in the details page format
    loaded_details = []
    for row in rows:
        date = row.Date.strftime("%d %B '%y").lstrip('0')
        loaded_details.append([row.Recipe, date, MEALTIME_CODES[row.Mealtime], LOCATION_CODES[row.Location]])

    # Close the connection
    connection.close()
    print('load_menu_details completed sucessfully')
    
    return loaded_details

def validate_filters(filters_str: str, is_details_page: bool):
    """ checks that filters_str is valid and returns a corrected string otherwise 
    
    :param filters_str: the filter string to check
    :param is_details_page: if current route is /details
    """
    
    # special case, if empty or None
    if filters_str == '' or not filters_str:
        return MFilters.get_default_filter()
    
    # convert to list to inspect each digit, and truncate if too long
    filters = list(filters_str[:MFilters.NUM_FILTERS.value])

    # add filters if too short (default toggled on)
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

def get_connection():
    """ returns a pyodbc connection to the database from environment variables """
    
    # get database connection information
    DB_SERVER_NAME = os.getenv('DB_SERVER_NAME')
    DB_NAME = os.getenv('DB_NAME')
    DB_USERNAME = os.getenv('DB_USERNAME')
    DB_PASSWORD = os.getenv('DB_PASSWORD')

    # Connect to database
    connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};"\
        f"Server=tcp:{DB_SERVER_NAME},1433;Database={DB_NAME};Uid={DB_USERNAME};"\
        f"Pwd={DB_PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

    # return connection
    return pyodbc.connect(connection_string)

# TODO shorten function (142 lines, yikes!)
def get_filtered_query(filters: str, food_name: str, exact_match: bool, cursor: pyodbc.Cursor):
    """ returns SQL query string for database using filters 

    :param filters: string determining selection filters. assume already validated.
    :param food_name: name of food to search
    :param exact_match: search for exact matches to food_name. (for details page)
    :param table_names: used for date filters
    """
    
    # convert to list
    filters = list(filters)

    # handle special char ' (SQL syntax does not allow ')
    if "'" in food_name:
        food_name = food_name.replace("'","''") 

    # determine whether to search for exact matches to food_name
    if exact_match:
        recipe_select = f"Recipe='{food_name}'" 
    else:
        recipe_select = f"(Recipe LIKE '% {food_name}%' OR Recipe LIKE '{food_name}%')" 

    # order clause - displays search results in order by these column values
    order_clause = ' ORDER BY Recipe, [Date], Mealtime'

    # Start building where clause (list of filters elements)
    where_clause = [recipe_select]

    # Mealtime Filters
    mealtime_filters=[]
    if not ('1' == filters[MFilters.BREAKFAST.value] == filters[MFilters.LUNCH.value] 
            == filters[MFilters.DINNER.value]):
        # add filter to query only if not all on
        if filters[MFilters.BREAKFAST.value] == '1':
            mealtime_filters.append(f'Mealtime=1')
        if filters[MFilters.LUNCH.value] == '1':
            mealtime_filters.append(f'Mealtime=2')   
        if filters[MFilters.DINNER.value] == '1':
            mealtime_filters.append(f'Mealtime=3')
        if mealtime_filters != []:
            mealtime_filters = f'({" OR ".join(mealtime_filters)})'
            where_clause.append(mealtime_filters)
    # else, search all mealtimes

    # Location filters
    loc_filters = []
    if not ('1' == filters[MFilters.KINS.value] == filters[MFilters.J2.value]
            == filters[MFilters.JCL.value]):
        # add filter to query only if not all on
        if filters[MFilters.KINS.value] == '1':
            loc_filters.append(f'Location=1')
        if filters[MFilters.J2.value] == '1':
            loc_filters.append(f'Location=2')
        if filters[MFilters.JCL.value] == '1':
            loc_filters.append(f'Location=3')
        if loc_filters != []:
            loc_filters = f'({" OR ".join(loc_filters)})'
            where_clause.append(loc_filters)
    # else, search all locations
    
    # Add time filters and return
    today = datetime.today()
    if filters[MFilters.TIME.value] == f'{MFilters.TIME_SHORT.value}':
        # TIME_SHORT case: searches to up to MFilters.TIME_SHORT_LIMIT - 1 days ahead
        start_date = today
        end_date = (today + timedelta(days=MFilters.TIME_SHORT_LIMIT.value - 1))
        if start_date.month == end_date.month:
            # both dates are in same month
            start_date = start_date.strftime("%m/%d/%Y")
            end_date = end_date.strftime("%m/%d/%Y")
            where_clause.append(f"([Date] BETWEEN '{start_date}' AND '{end_date}')")
            
            # combine query elements to form full query and return
            return f'SELECT * from {get_table_name(today)} WHERE ' + ' AND '.join(where_clause) + order_clause
        else:
            # end_date is in another month and thus table. Must join tables
            start_date_str = start_date.strftime("%m/%d/%Y")
            where_clause.append(f"([Date] >= '{start_date_str})'")
            table1 = f'SELECT * from {get_table_name(start_date)} WHERE' + ' AND '.join(where_clause)
            where_clause.pop() # remove previous date filter, preserving other filters
            start_date = start_date.strftime("%m/%d/%Y")
            end_date = end_date.strftime("%m/%d/%Y")
            where_clause.append(f"([Date] BETWEEN '{start_date}' AND '{end_date}')")
            table2 = f'SELECT * from {get_table_name(end_date)} WHERE' + ' AND '.join(where_clause)
            
            # combine query elements to form full query and return
            return f'{table1} UNION {table2} {order_clause}'
        
    elif filters[MFilters.TIME.value] == f'{MFilters.TIME_FUTURE.value}':
        # TIME_FUTURE case: searches everything after today
        start_date = today
        today_str = today.strftime("%m/%d/%Y")
        where_clause.append(f"([Date] >= '{today_str}')")
        table1 = f'SELECT * from {get_table_name(today)} WHERE ' + ' AND '.join(where_clause)

        # case: check if date range extends to next month and thus need to join tables
        month = start_date.month + 1 if start_date.month != 12 else 1
        year = start_date.year if month != 1 else start_date.year + 1
        next_month = datetime(year, month, 1)
        next_tname = get_table_name(next_month)
        if is_valid_tname(cursor, next_tname):
            # Add next month's table
            where_clause.pop() # remove previous date filter, preserving other filters
            table2 = f'SELECT * from {next_tname} WHERE ' + ' AND '.join(where_clause)

            # combine query elements to form full query and return
            return f'{table1} UNION {table2} {order_clause}'
        else:
            # date range ends within this month. combine query elements and return
            return f'{table1} {order_clause}'
    
    else:
        # TIME ALL case: searches from all tables
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

        # combine query elements to form full query and return
        where_clause = ' AND '.join(where_clause)
        select_clauses = [f'SELECT * from {table} WHERE {where_clause}' for table in tables]
        return ' UNION '.join(select_clauses) + order_clause

def get_table_name(date: datetime):
    """ returns table name in database for a date """
    # table names in format (prefix)_(year)_(month)
    DB_TABLE_PREFIX = os.getenv('DB_TABLE_PREFIX')
    return f'{DB_TABLE_PREFIX}_{date.year}_{date.month}'

def is_valid_tname(cursor: pyodbc.Cursor, table_name: str):
    """ Returns true if table_name is a valid table name (present in cursor's database), false otherwise """
    return cursor.tables(table=table_name, tableType='TABLE').fetchone() is not None
