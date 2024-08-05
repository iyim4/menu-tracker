# app.py
# Website to search availability of foods from UT Austin dining halls

from flask import Flask, request, render_template
from searchdb import load_menu_details, load_menu_home, DEFAULT_MFILTER, MFilters, validate_filters, recode_timefilter
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    """ home page that includes searching """

    # Initialize variables
    loaded_menu = []
    food_name = request.args.get('search')
    filters_str = request.args.get('filters', DEFAULT_MFILTER) 
    filters_str = validate_filters(filters_str, False)

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
                loaded_menu = load_menu_home(food_name, filters_str)

                return render_template('home.html', menu = loaded_menu, search = food_name, filters = filters_str)
        
        # search bar (preserves last filter setting)
        loaded_menu = load_menu_home(food_name, filters_str)

    # default, user has not searched yet
    return render_template('home.html', menu = loaded_menu, search = food_name, filters = filters_str)

@app.route('/details', methods=['GET'])
def details():
    """ shows historic and future availability of specific food over a large timespan """

    # Get args
    filters_str = request.args.get('filters', DEFAULT_MFILTER) 
    filters_str = validate_filters(filters_str, False) # false because haven't recoded filters yet - see below
    food_name = request.args.get('search')

    # build today and tomorrow strings (for colors)
    today_str = get_datestr(datetime.today())
    tmr_str = get_datestr(datetime.today() + timedelta(days=1))

    # Get details
    if food_name:
        # check if a button was clicked and update results accordingly
        for i in range(MFilters.NUM_FILTERS.value):
            # check which button (filter1, filter2, ...) was clicked
            if 'filters{}'.format(i) in request.args: 
                # toggle the specific filter option. for time, 'add' 1 (details page special: future/all time)
                filters_list = list(filters_str)
                filters_list[i] = '0' if filters_list[i] == '1' else '1'
                filters_str = ''.join(filters_list)

                # query database with new filters
                recoded_filter = recode_timefilter(filters_str)
                loaded_details = load_menu_details(food_name, recoded_filter)

                return render_template('details.html', menu = loaded_details, search = food_name, 
                                       filters = filters_str, today_str = today_str, tmr_str = tmr_str)
        
        # else, initial load of details page. 
        recoded_filter = recode_timefilter(filters_str)
        loaded_details = load_menu_details(food_name, recoded_filter)
    else:
        loaded_details = []
        food_name = 'Error retrieving food name'

    return render_template('details.html', search = food_name, menu = loaded_details, 
                           today_str = today_str, tmr_str = tmr_str)

def get_datestr(date: datetime):
    """ returns date in details page format """
    return date.strftime("%d %B '%y").lstrip('0')

@app.errorhandler(404)
def not_found(e):
    message = 'Page Not Found'
    return render_template('error.html', message=message)

@app.errorhandler(500)
def not_found(e):
    message = 'Error connecting to or searching database'
    return render_template('error.html', message=message)

# for running locally
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
