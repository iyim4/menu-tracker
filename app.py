# app.py
# Website to search availability of foods from UT Austin dining halls

from flask import Flask, request, render_template
from datetime import datetime, timedelta
import pyodbc
import os
from enum import Enum
from testdef import get_filtered_query, MFilters, DEFAULT_MFILTER

# mapping from database codes to strings
MEALTIME_CODES = ['ERROR', 'Breakfast', 'Lunch', 'Dinner']
LOCATION_CODES = ['ERROR', 'Kins', 'J2', 'JCL']


# get environment variables (for connecting to database)
DB_SERVER_NAME = os.getenv('DB_SERVER_NAME')
DB_NAME = os.getenv('DB_NAME')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')

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
    filters_str = request.args.get('filters', DEFAULT_MFILTER) 
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

    # default, user has not searched yet
    return render_template('home.html', menu = loaded_menu, search = food_name, filters = filters_str)

@app.route('/details', methods=['GET'])
def details():
    """ shows historic and future availability of specific food over a large timespan """

    # Get args
    filters_str = request.args.get('filters', DEFAULT_MFILTER) 
    filters_str = DEFAULT_MFILTER if filters_str == '' else filters_str
    food_name = request.args.get('search')

    # Get details
    if food_name:
        # check if a button was clicked and update results accordingly
        for i in range(MFilters.NUM_FILTERS.value):
            # check which button (filter1, filter2, ...) was clicked
            if 'filters{}'.format(i) in request.args: 
                # toggle the specific filter option
                filters_list = list(filters_str)
                filters_list[i] = '0' if filters_list[i] == '1' else '1'
                filters_str = ''.join(filters_list)

                # recode filters (details page special: toggle between future and all time)
                filters_list[0] = '2' if filters_list[0] == '1' else '1'
                recoded_filters = ''.join(filters_list)

                # query database with new filters
                loaded_details = load_details(food_name, recoded_filters)

                return render_template('details.html', menu = loaded_details, search = food_name, filters = filters_str)
        
        # else, initial load of details page. show details with default filter
        loaded_details = load_details(food_name, filters_str)
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
    query = get_filtered_query(filters, food_name, True, cursor)
    print(f'searching for {food_name} in load_details with filters: {filters} and query {query}')
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

# for running locally
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
