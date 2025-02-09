# app.py
# Website to search upcoming availability of foods from UT Austin dining halls

from datetime import datetime, timedelta
from flask import Flask, request, render_template
from searchdb import load_menu_details, load_menu_home, MFilters
from predict_dates import predict_future_date

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    """ home page that includes searching """

    # Initialize variables and get arguments from requests
    loaded_menu = []  # stores foods and availability information
    food_name = request.args.get('search')  # user input, food to search for
    filters_str = request.args.get('filters', MFilters.get_default_filter())  # search filters
    filters_str = validate_filters(filters_str)  # correct filter errors if necessary

    if not(request.method == 'GET' and food_name):
        # initial load of page
        return render_template('home.html', menu = loaded_menu, search = food_name, filters = filters_str)
    else:
        # respond to user interaction
        # check if interaction was toggling a filter - update filters_str
        if 'filtersKDIN' in request.args:
            filters_str = '0001100' if (request.args.get('filtersKDIN') == '0') else '0110011'
       
        elif 'filtersJLUN' in request.args:
            filters_str = '0010011' if (request.args.get('filtersJLUN') == '0') else '0101100'
        else:
            # check generic filters
            for i in range(MFilters.NUM_FILTERS.value):
                if 'filters{}'.format(i) in request.args: 
                    # toggle the specific filter option on/off
                    filters_list = list(filters_str)
                    filters_list[i] = '0' if filters_list[i] == '1' else '1'
                    filters_str = ''.join(filters_list)
                    break
        # otherwise, if no filters found, user searched for a new food. Previous filters are preserved

        # query database with updated filters and return
        loaded_menu = load_menu_home(food_name, filters_str)
        return render_template('home.html', menu = loaded_menu, search = food_name, filters = filters_str)

@app.route('/details', methods=['GET'])
def details():
    """ shows historic and future availability of specific food over a large timespan """

    # Get arguments from requests
    food_name = request.args.get('search', '')  # user input, food to search for
    filters_str = request.args.get('filters', MFilters.get_default_filter())  # search filters
    filters_str = validate_filters(filters_str)  # correct filter errors if necessary

    # build today and tomorrow strings (for colors)
    today_str = get_datestr(datetime.today())
    tmr_str = get_datestr(datetime.today() + timedelta(days=1))

    # Get details
    if food_name != '':
        # check if a button was clicked and update results accordingly
        for i in range(MFilters.NUM_FILTERS.value):
            # check which button (filter1, filter2, ...) was clicked
            if 'filters{}'.format(i) in request.args: 
                # toggle the specific filter option. for time, 
                filters_list = list(filters_str)
                filters_list[i] = '0' if filters_list[i] == '1' else '1'
                filters_str = ''.join(filters_list)

                # recode filter for details page toggles: future/all time visibility
                filters_list[0] = '1' if filters_list[0] == '0' else '2'
                recoded_filter = ''.join(filters_list)
                
                # query database with filters for the future and past
                filters_list[0] = str(MFilters.TIME_FUTURE.value)
                future_menu_filters = ''.join(filters_list)
                future_menu = load_menu_details(food_name, future_menu_filters)

                filters_list[0] = str(MFilters.TIME_PAST.value)
                past_menu_filters = ''.join(filters_list)
                past_menu = load_menu_details(food_name, past_menu_filters)

                prediction_entry = predict_future_date (food_name)

                return render_template('details.html', future_menu = future_menu, past_menu = past_menu, 
                                       search = food_name, filters = filters_str, today_str = today_str, 
                                       tmr_str = tmr_str, prediction_entry = prediction_entry)
        
        # else, no button was clicked. It was the initial load of details page. 

        # query database with filters for the future and past
        future_menu_filters = str(MFilters.TIME_FUTURE.value) + filters_str[1:]
        future_menu = load_menu_details(food_name, future_menu_filters)

        past_menu_filters = str(MFilters.TIME_PAST.value) + filters_str[1:]
        past_menu = load_menu_details(food_name, past_menu_filters)

    else:
        # Somehow got '' (can happen when user manually types in URL)
        loaded_details = []
        food_name = 'Error retrieving food name. No'

    prediction_entry = predict_future_date (food_name)

    return render_template('details.html', search = food_name, future_menu = future_menu, 
                           past_menu = past_menu, today_str = today_str, tmr_str = tmr_str, 
                           prediction_entry = prediction_entry)

def validate_filters(filters_str: str):
    """ checks that filters_str is valid and returns a corrected string otherwise """

    # special case, if empty or None
    if filters_str == '' or not filters_str:
        return MFilters.get_default_filter()
    
    # convert to list to inspect each digit, and truncate if too long
    filters = list(filters_str[:MFilters.NUM_FILTERS.value])

    # add filters if too short (default toggled on)
    while len(filters) < MFilters.NUM_FILTERS.value:
        filters.append('1')

    # check each digit is '0' or '1'
    for index in range(MFilters.NUM_FILTERS.value):
        digit = f'{filters[index]}'
        if digit != '0' and digit != '1':
            filters[index] = '1'

    # return as string
    return ''.join(filters)

def get_datestr(date: datetime):
    """ returns date in details page format """
    return date.strftime("%d %B '%y").lstrip('0')

# TODO handle more errors
@app.errorhandler(404)
def not_found(e):
    message = 'Page Not Found'
    return render_template('error.html', message=message)

@app.errorhandler(500)
def not_found(e):
    # There was an error connecting to or searching the database
    food_name = request.args.get('search')  # user input, food to search for
    message = f'Error searching for {food_name} in the database'
    return render_template('error.html', message=message)

@app.route('/overview', methods=['GET'])
def overview():
    return render_template('overview.html')

@app.route('/about', methods=['GET'])
def about():
    return render_template('about.html')

# # for running locally
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', debug=True)

# attempt to fix 503 error
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))  # Use the PORT environment variable set by Azure
    app.run(host='0.0.0.0', port=port, debug=True)
