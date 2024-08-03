# app.py
# Website to search availability of foods from UT Austin dining halls

from flask import Flask, request, render_template
from datetime import datetime, timedelta
import pyodbc
import os
from enum import Enum

# mapping from database codes to strings
MEALTIME_CODES = ['ERROR', 'Breakfast', 'Lunch', 'Dinner']
LOCATION_CODES = ['ERROR', 'Kins', 'J2', 'JCL']
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

# get environment variables (for connecting to database)
DB_SERVER_NAME = os.getenv('DB_SERVER_NAME')
DB_NAME = os.getenv('DB_NAME')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_TABLE_NAME = os.getenv('DB_TABLE_NAME') # temporary. will implement date searches later.

app = Flask(__name__)

def load_menu(food_name: str, filters: str): 
    """ load all filtered search results for food from database in home page format 
    :param food_name: name of food to search
    :param filters: string representing filter settings
    """

    # Connect to database
    connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{DB_SERVER_NAME},1433;Database={DB_NAME};"\
        f"Uid={DB_USERNAME};Pwd={DB_PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor()

    # TODO ensure that table has correct format (my menu format)

    # Get and execute the SQL query
    query = get_filtered_query(filters, food_name, False)
    print(f'searching for {food_name} in load_menu with filters: {filters} and query {query}')
    cursor.execute(query)

    # Fetch all rows
    rows = cursor.fetchall()

    # Extract data and store into a list
    result_arr = []
    today = datetime.today()
    today = datetime(today.year, today.month, today.day)
    tomorrow = today + timedelta(days=1)
    for row in rows:
        date = row.Date
        date = 'Today' if date == today else ('Tomorrow' if date == tomorrow else f'{date.strftime("%A")}')
        result_arr.append([row.Recipe, date, MEALTIME_CODES[row.Mealtime], LOCATION_CODES[row.Location]])

    # Close the connection
    connection.close()
    print('search complete')
    
    return result_arr

@app.route('/', methods=['GET'])
def home():
    """ home page that includes searching """

    # Initialize variables
    loaded_menu = []
    food_name = request.args.get('search')
    filters_str = request.args.get('filters', '1111111') 
    # filters_str is a string that represents filter settings
    # filters are stored as a string of numbers. each digit is used to determine
    # a specific filter setting at the index corresponding to the MFilters enumeration
    # filters are used to filter food search results

    # respond to user interaction
    if request.method == 'GET' and food_name:
        # filter toggles
        for i in range(MFilters.NUM_FILTERS.value):
            # check which button (filter1, filter2, ...) was clicked
            if 'filters{}'.format(i) in request.args: 
                # toggle the specific filter option
                filters_list = list(filters_str)
                filters_list[i] = '0' if filters_list[i] == '1' else '1'
                filters_str = ''.join(filters_list)

                # query database with new filters
                loaded_menu = load_menu(food_name, filters_str)

                return render_template('home.html', menu = loaded_menu, search = food_name, filters = filters_str)
        
        # search bar (preserves last filter setting)
        loaded_menu = load_menu(food_name, filters_str)
        # print(loaded_menu)

    # default, user has not searched yet
    return render_template('home.html', menu = loaded_menu, search = food_name, filters = filters_str)

@app.route('/details', methods=['GET'])
def details():
    """ shows historic and future availability of specific food over a large timespan """

    # Get args
    filters = request.args.get('filters', '0111111') 
    food_name = request.args.get('search')

    # TODO implement toggles here.

    # Get details
    if food_name:
        loaded_details = load_details(food_name, filters)
    else:
        loaded_details = []
        food_name = 'Error retrieving food name'

    return render_template('details.html', search = food_name, menu = loaded_details)

def load_details(food_name, filters):
    """ load filtered details for food from database in details page format 
    :param food_name: name of food to search
    :param filters: string representing filter settings
    """

    # Connect to database
    connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{DB_SERVER_NAME},1433;Database={DB_NAME};"\
        f"Uid={DB_USERNAME};Pwd={DB_PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor()

    # TODO ensure that table has correct format (my menu format)

    # Get and execute the SQL query
    query = get_filtered_query(filters, food_name, True)
    print(f'searching for {food_name} in load_menu with filters: {filters} and query {query}')
    cursor.execute(query)

    # Fetch all rows
    rows = cursor.fetchall()

    # Extract data and store into a list
    loaded_details = []
    for row in rows:
        date = row.Date.strftime("%d %B '%y").lstrip('0')
        loaded_details.append([row.Recipe, date, MEALTIME_CODES[row.Mealtime], LOCATION_CODES[row.Location]])

    # Close the connection
    connection.close()
    print('load details search complete')
    
    return loaded_details

def get_filtered_query(filters: str, food_name: str, exact_match: bool):
    """ returns SQL query string for database using filters 

    :param filters: string determining selection filters
    :param food_name: name of food to search
    :param exact_match: determines whether to search for exact matches to food_name
    """
    
    # convert to list
    filters = list(filters[:MFilters.NUM_FILTERS.value])
    # TODO error checking. currently, assumes filter is on if number is not 0

    # determine whether to search for exact matches to food_name
    recipe_select = f"Recipe='{food_name}'" if exact_match else f"(Recipe LIKE '% {food_name}%' OR Recipe LIKE '{food_name}%')" 

    # special, default cases
    if filters == [f'{MFilters.TIME_ALL.value}', '1', '1', '1', '1', '1', '1']:
        return f"SELECT * FROM {DB_TABLE_NAME} WHERE {recipe_select} ORDER BY Recipe, [Date], Mealtime"
    elif filters == [f'{MFilters.TIME_FUTURE.value}', '1', '1', '1', '1', '1', '1']:
        date = datetime.today().strftime("%m/%d/%Y")
        return f"SELECT * FROM {DB_TABLE_NAME} WHERE {recipe_select} AND [Date] >= {date} ORDER BY Recipe, [Date], Mealtime"

    # Base selection
    query = [f"SELECT * FROM {DB_TABLE_NAME} WHERE {recipe_select} "]

    # Time filter
    today = datetime.today()
    if filters[MFilters.TIME.value] == f'{MFilters.TIME_SHORT.value}':
        start_date = today.strftime("%m/%d/%Y")
        end_date = (today + timedelta(days=2)).strftime("%m/%d/%Y")
        query.append(f"[Date] BETWEEN '{start_date}' AND '{end_date}'")
    elif filters[MFilters.TIME.value] == f'{MFilters.TIME_FUTURE}':
        today = today.strftime("%m/%d/%Y")
        query.append(f"[Date] >= '{today}'")
    # else, search all time

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
            query.append(mealtime_filters)
    # else, search all mealtimes

    # Location filters
    loc_fil = []
    if not ('1' == filters[MFilters.KINS.value] == filters[MFilters.J2.value] == filters[MFilters.JCL.value]):
        if filters[MFilters.KINS.value] == '1':
            loc_fil.append(f'Location=1')
        if filters[MFilters.J2.value] == '1':
            loc_fil.append(f'Location=2')
        if filters[MFilters.JCL.value] == '1':
            loc_fil.append(f'Location=3')
        if loc_fil != []:
            loc_fil = f'({" OR ".join(loc_fil)})'
            query.append(loc_fil)
    # else, search all locations

    # combine query elements to form full query
    query = ' AND '.join(query) + ' ORDER BY Recipe, [Date], Mealtime'
    return query

# for running locally
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
