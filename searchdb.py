# searchdb.py
# provides methods to search database for availability of foods from UT Austin dining halls
# assumes connection details in environment variables
# TODO change print statements to logging statements

from datetime import datetime, timedelta
from enum import Enum
import pyodbc
import pytz
import os
import pandas as pd

# mapping from database codes to strings
NUM_PREDICTIONS = 3 # Number of dates to predict for each food 
MEALTIME_CODES = ['ERROR', 'Breakfast', 'Lunch', 'Dinner']
ENTIRE_DATABASE_CSV_FILENAME = 'entire_database.csv'
class LocationCodesNum(Enum):
    ERR = 0
    KINS = 1
    J2 = 2
    JCL = 3

    # def get_name (code): return location codes str
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
    TIME_PAST = 2
    TIME_SHORT_LIMIT = 3 # the number of days TIME_SHORT displays

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
    today = get_today()
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
    query = get_filtered_query(filters, food_name, True, cursor)

    # Execute query
    print(f'load_menu_details searching for {food_name} with filters {filters} and query {query}')
    cursor.execute(query)

    # Fetch results of query
    rows = cursor.fetchall()

    # Extract data and store into a list in the details page format
    loaded_details = []
    for row in rows:
        date = row.Date.strftime("%d %B '%y").lstrip('0')
        loaded_details.append([date, MEALTIME_CODES[row.Mealtime], LOCATION_CODES[row.Location]])

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
def get_filtered_query(filters: str, food_name: str, exact_match: bool, 
                       cursor: pyodbc.Cursor):
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
    today = get_today()
    if filters[MFilters.TIME.value] == f'{MFilters.TIME_SHORT.value}':
        # TIME_SHORT case: searches to up to MFilters.TIME_SHORT_LIMIT - 1 days ahead
        # For the main menu search
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
        # TIME_FUTURE case: searches today and beyond
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
        # TIME PAST case: searches everything before today, exclusive
        today = get_today()
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
        
        # combine query elements to form partial query
        where_clause_partial = ' AND '.join(where_clause)
        select_clauses = [f'SELECT * from {table} WHERE {where_clause_partial}' for table in tables]

        # add this month's table and date filter
        where_clause.append(f"([Date] >= '{today.strftime('%m/%d/%Y')}')")
        where_clause_final = ' AND '.join(where_clause)
        select_clauses.append(f'SELECT * from {get_table_name(temp_date)} WHERE {where_clause_final}')

        # combine query elements to form full query and return
        return ' UNION '.join(select_clauses) + order_clause

def get_table_name(date: datetime):
    """ returns table name in database for a date """
    # table names in format (prefix)_(year)_(month)
    DB_TABLE_PREFIX = os.getenv('DB_TABLE_PREFIX')
    return f'{DB_TABLE_PREFIX}_{date.year}_{date.month}'

def is_valid_tname(cursor: pyodbc.Cursor, table_name: str):
    """ Returns true if table_name is a valid table name (present in cursor's database), false otherwise """
    return cursor.tables(table=table_name, tableType='TABLE').fetchone() is not None

def get_today() -> datetime:
    """ Returns the today's date, Austin time """
    # Get the current time in UTC
    utc_now = datetime.now(pytz.utc)

    # Convert the current time to CST
    cst_now = utc_now.astimezone(pytz.timezone('US/Central'))

    # Extract just the date
    cst_today = datetime(cst_now.year, cst_now.month, cst_now.day)

    # Print the new datetime object
    return cst_today

def download_database_csv(cursor: pyodbc.Cursor):
    # get dates to search from all tables
    today = get_today()
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

    # combine query elements to full query
    order_clause = ' ORDER BY Recipe, [Date], Mealtime'
    select_clauses = [f'SELECT * from {table}' for table in tables]
    query = ' UNION '.join(select_clauses) + order_clause

    # Execute query
    print (f"Download_database_csv: Executing query {query}.")
    # smaller query for safety - delete this line later
    query = "select * from [dbo].[menu_2025_2] UNION select * from [dbo].[menu_2025_1]"
    cursor.execute(query)

    # Fetch results of query
    rows = cursor.fetchall()

    # Extract data and store into a list in the details page format
    entire_db = []
    for row in rows:
        # add One Hot Encoding for Mealtimes and Locations. format:
        # food name, date, isBreakfast?, isLunch?, isDinner?, isKins?, isJ2?, isJCL?
        entire_db.append([row.Recipe, row.Date, int(row.Mealtime == 1), 
                          int(row.Mealtime == 2), int(row.Mealtime == 3), 
                          int(row.Location == 1), int(row.Location == 2), 
                          int(row.Location == 3)])

    # Converting entire db to a dataframe & then to .CSV
    entire_db_df = pd.DataFrame(entire_db)
    entire_db_df.to_csv(ENTIRE_DATABASE_CSV_FILENAME, index=False)

    print (f"download_entire_database_csv completed: Saved entire database into {ENTIRE_DATABASE_CSV_FILENAME}")

PREDICTION_TABLE_NAME = 'predict_test'
def save_predictions_to_db(prediction_array, cursor, location_code):
    """
    prediction array: 2d array formated like food, date1, date2, date3
    location: must be in LOCATION_CODES
    cursor: connection to database
    """
    # Write each prediction to the database
    for prediction in prediction_array:
        # write each date
        food_name = prediction[0]
        assert isinstance(food_name, str), f"Expected datetime object, got {type(food_name)} instead."
        for i in range(1, NUM_PREDICTIONS + 1):
            date = prediction[i]
            date = datetime (date.year, date.month, date.day)
            assert isinstance(date, datetime), f"Expected datetime object, got {type(date)} instead."
            instr = f"INSERT INTO {PREDICTION_TABLE_NAME} (Recipe, [Date], [Location]) VALUES (?, ?, ?)"
            cursor.execute(instr, food_name, date, location_code) 

    print (f"done adding predictions to {PREDICTION_TABLE_NAME}")

def get_predictions_from_db(food_name):
    """ read from predictions """
    
    # Connect to database
    connection = get_connection()
    cursor = connection.cursor()

    query = f"SELECT * FROM {PREDICTION_TABLE_NAME} WHERE Recipe='{food_name}' ORDER BY [Date]"

    # Execute query
    print(f'get_predictions_from_db searching for {food_name} with query {query}')
    cursor.execute(query)

    # Fetch results of query
    rows = cursor.fetchall()

    # Extract data and store into a list in the details page format
    predictions = []
    for row in rows:
        date = row.Date.strftime("%d %B '%y").lstrip('0')
        predictions.append([date, LOCATION_CODES[row.Location]])

    # Close the connection
    connection.close()
    
    print ("done fetching predictions")
    return predictions