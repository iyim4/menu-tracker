# app.py
# Website to search availability of foods from UT Austin dining halls

from flask import Flask, request, render_template
from datetime import datetime, timedelta
import pyodbc
import os

# mapping from database codes to strings
MEALTIME_CODES = ['ERROR', 'Breakfast', 'Lunch', 'Dinner']
LOCATION_CODES = ['ERROR', 'Kins', 'J2', 'JCL']

# get environment variables (for connecting to database)
DB_SERVER_NAME = os.getenv('DB_SERVER_NAME')
DB_NAME = os.getenv('DB_NAME')
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_TABLE_NAME = os.getenv('DB_TABLE_NAME') # temporary. will implement date searches later.

TIMEFRAME_WEEK = 1
TIMEFRAME_MONTH = 2
TIMEFRAME_ALLTIME = 3

app = Flask(__name__)

def load_menu(food): 
    """ load food and details from database """

    # Connect to database
    connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{DB_SERVER_NAME},1433;Database={DB_NAME};"\
        f"Uid={DB_USERNAME};Pwd={DB_PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor()

    # TODO ensure that table has correct format (my menu format)

    # execute the SQL query
    print(f'searching for {food} in load_menu...')
    instr = f"SELECT * FROM {DB_TABLE_NAME} WHERE Recipe LIKE '% {food}%' OR Recipe LIKE '{food}%' ORDER BY Recipe, [Date], Mealtime"
    cursor.execute(instr)

    # fetch all rows
    rows = cursor.fetchall()

    # store each row into a list
    result_arr = []
    today = datetime.today()
    today = datetime(today.year, today.month, today.day)
    tomorrow = today + timedelta(days=1)
    for row in rows:
        date = row.Date
        date = 'Today' if date == today else ('Tomorrow' if date == tomorrow else f'{date.strftime("%A")}')
        result_arr.append([row.Recipe, date, MEALTIME_CODES[row.Mealtime], LOCATION_CODES[row.Location]])

    # close the connection
    connection.close()
    print('search complete')
    
    return result_arr

@app.route('/', methods=['GET'])
def home():
    """ home page that includes searching """

    # initialize variables
    loaded_meals = []
    search_result_text = 'Enter the name of a food in the search bar'

    # retrieve search bar input from database
    food = request.args.get('search')
    if request.method == 'GET' and food is not None:
        loaded_meals = load_menu(food)
        search_result_text = f'Results for {food}'
        
    return render_template('home.html', meals = loaded_meals, search_result_string = search_result_text)

@app.route('/details', methods=['GET'])
def details():
    """ detailed view of a food: shows entries from a large timespan """

    timeframe = TIMEFRAME_ALLTIME
    food_name = request.args.get('food')
    if food_name is not None:
        loaded_details = load_details(food_name, timeframe)
    else:
        loaded_details = []
        food_name = 'Error retrieving food name'
    return render_template('details.html', food_name = food_name, meals = loaded_details)

def load_details(food_name, timeframe):
    """ load details of food_name """

    # Connect to database
    connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{DB_SERVER_NAME},1433;Database={DB_NAME};"\
        f"Uid={DB_USERNAME};Pwd={DB_PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor()

    # TODO ensure that table has correct format (my menu format)

    # Select SQL query based on timeframe
    print(f'searching for {food_name} in load_details with code {timeframe}...')
    if timeframe == TIMEFRAME_MONTH:
        # search 2 weeks behind and ahead
        print('in timeframe month')
    elif timeframe == TIMEFRAME_ALLTIME:
        # search alltime
        instr = f"SELECT * FROM {DB_TABLE_NAME} WHERE Recipe LIKE '% {food_name}%' OR Recipe LIKE '{food_name}%' ORDER BY Recipe, [Date], Mealtime"
    else:
        # search next 7 days
        print('in timeframe week')

    # execute the SQL query
    cursor.execute(instr)

    # fetch all rows
    rows = cursor.fetchall()

    # store each row into a list
    loaded_details = []
    for row in rows:
        date = row.Date.strftime("%d %B '%y").lstrip('0')
        loaded_details.append([row.Recipe, date, MEALTIME_CODES[row.Mealtime], LOCATION_CODES[row.Location]])

    # close the connection
    connection.close()
    print('load details search complete')
    
    return loaded_details

if __name__ == '__main__':
    """ run locally """
    app.run(host='0.0.0.0', debug=True)
