# app.py
# Retrieves data from database and displays on localhost

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

app = Flask(__name__)

def load_menu(food): 
    """ load menu from database """

    # Connect to database
    connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server=tcp:{DB_SERVER_NAME},1433;Database={DB_NAME};"\
        f"Uid={DB_USERNAME};Pwd={DB_PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor()

    # TODO ensure that table has correct format (my menu format)

    # execute the SQL query
    print(f'searching for {food}...')
    instr = f"SELECT * FROM {DB_TABLE_NAME} WHERE Recipe LIKE '% {food}%' OR Recipe LIKE '{food}%' ORDER BY Recipe, [Date], Mealtime"
    cursor.execute(instr)

    # fetch all rows
    rows = cursor.fetchall()

    # store each row into a list
    result_arr = []
    today = datetime(2024, 7, 28, 0, 0, 0)
    tomorrow = today + timedelta(days=1)
    for row in rows:
        date = row.Date
        date = 'Today' if date == today else ('Tomorrow' if date == tomorrow else f'{date.strftime("%A")}')
        result_arr.append([row.Recipe, date, MEALTIME_CODES[row.Mealtime], LOCATION_CODES[row.Location]])

    # close the connection
    connection.close()
    print('search complete')
    
    return result_arr

@app.route('/', methods=['GET', 'POST'])
def render_app():
    """ renders app """

    # initialize variables
    loaded_meals = []
    search_result_text = 'Enter the name of a food in the search bar'

    # retrieve search bar input from database
    if request.method == 'POST':
        food = request.form.get('food_search')
        loaded_meals = load_menu(food)
        search_result_text = f'Results for {food}'
        
    return render_template('home.html', meals = loaded_meals, search_result_string = search_result_text)

if __name__ == '__main__':
    """ run locally """
    app.run(host='0.0.0.0', debug=True)
