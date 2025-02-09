# -*- coding: utf-8 -*-
"""predict_future_date (1).ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1aO43g_g-hVP4kA7CFpG5Eb-MXKtZrHl3
"""
# print ("predict_future date: start import")
# TODO Remove imporats
import pandas as pd
import datetime as dt
from sklearn.model_selection import train_test_split
from sklearn import model_selection
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from searchdb import LocationCodesNum, save_predictions_to_db, NUM_PREDICTIONS

# print ("end import")

# TODO header comments and DOUBLE CHECK in line comments
def make_food_model (food_dining_db):
    """ 
    Trains the model for this dining hall
    :food_dining_db: the dataframe of a certain dining hall (food_kins_db, food_j2_db, OR food_jcl_db)
    """
    # Removes NaNs
    food_dining_db = food_dining_db.dropna(subset=['Gap'])
    evaluation_results = {}

    # Normalizes data
    gaps_dining = food_dining_db['Gap'].values.reshape(-1, 1)
    y_dining = food_dining_db['Gap']

    # Trains the data
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(gaps_dining, y_dining, test_size=0.2, random_state=42)
    model.fit(X_train, y_train)

    # Makes predictions to test the model
    y_test_pred = model.predict(X_test)

    # Evaluate the model using test set
    mae = mean_absolute_error(y_test, y_test_pred)  # Mean Absolute Error
    mse = mean_squared_error(y_test, y_test_pred)  # Mean Squared Error
    r2 = r2_score(y_test, y_test_pred)  # R² Score

    # Store evaluation metrics
    evaluation_results = {'MAE': mae, 'MSE': mse, 'R²': r2}
    # TODO for testing purposes

    return model

def predict_food_days(model, food_dining_db):
    """ 
    Makes predictions for future 
    :model: from make_food_model
    :food_dining_db: the dataframe of a certain dining hall (food_kins_db, food_j2_db, OR food_jcl_db)
    """
    food_groups = food_dining_db.groupby('Food')
    predictions = {}

    # Make future predictions for each food
    for food, group in food_groups:
        # Predict the next `x` gaps for this specific food
        predicted_dates = [group['Date(Datetime)'].iloc[-1]]  # Use the last date for this specific food group
        last_gap = group['Gap'].iloc[-1]  # The last observed gap for this food

        for _ in range(NUM_PREDICTIONS):
            predicted_gap = model.predict([[last_gap]])  # Predict next gap based on the last gap
            next_date = predicted_dates[-1] + pd.Timedelta(days=predicted_gap[0])  # Add predicted gap to last date
            predicted_dates.append(next_date)  # Append the predicted date
            last_gap = predicted_gap[0]  # Update last_gap to the predicted gap for the next iteration

        predictions[food] = predicted_dates[1:]  # Return the predicted dates (excluding the first one, which is the last known date)
    
    return pd.DataFrame.from_dict(predictions)


def make_predictions (cursor, csv_file_name):
    # Load the dataset from csv
    names = ['Food', 'Date(String)', 'Breakfast', 'Lunch', 'Dinner', 'Kins', "J2", "JCL"]
    food_db = pd.read_csv(csv_file_name, header=None)
    food_db = food_db[1:]   # drop first row; it doesn't contain any data
    food_db.columns = names

    # Convert date strings into datetime objects
    food_db['Date(Datetime)'] = pd.to_datetime(food_db["Date(String)"])

    # Drop date string column
    food_appearance_db = food_db.drop(columns=['Date(String)'])

    # Creates a dataframe for each dining hall AND adds "Gap" column for time differences
    #Kins
    food_kins_db = food_appearance_db[food_appearance_db["Kins"] == 1].drop(columns=['J2', 'JCL'])
    food_kins_db = food_kins_db.drop_duplicates(subset=['Date(Datetime)', 'Food'], keep='first')
    food_kins_db["Gap"] = food_kins_db.groupby('Food')['Date(Datetime)'].diff().dt.days
    # #J2
    # food_j2_db = food_appearance_db[food_appearance_db["J2"] == 1].drop(columns=['Kins', 'JCL'])
    # food_j2_db = food_j2_db.drop_duplicates(subset=['Date(Datetime)', 'Food'], keep='first')
    # food_j2_db["Gap"] = food_j2_db.groupby('Food')['Date(Datetime)'].diff().dt.days
    # #JCL
    # food_jcl_db = food_appearance_db[food_appearance_db["JCL"] == 1].drop(columns=['J2', 'Kins'])
    # food_jcl_db = food_jcl_db.drop_duplicates(subset=['Date(Datetime)', 'Food'], keep='first')
    # food_jcl_db["Gap"] = food_jcl_db.groupby('Food')['Date(Datetime)'].diff().dt.days

    # Train the models and get predictions for each dining hall
    kins_model = make_food_model(food_kins_db)
    kins_predicted_future_dates = predict_food_days(kins_model, food_kins_db).transpose()

    # j2_model = make_food_model(food_j2_db)
    # j2_predicted_future_dates = predict_food_days(j2_model, food_j2_db).transpose()

    # jcl_model = make_food_model(food_jcl_db)
    # jcl_predicted_future_dates = predict_food_days(jcl_model, food_jcl_db).transpose()

    # FORMAT: Turn 'food names' from index into a new column
    kins_predicted_food_dates_reset = kins_predicted_future_dates.reset_index()
    # j2_predicted_food_dates_reset = j2_predicted_future_dates.reset_index()
    # jcl_predicted_food_dates_reset = jcl_predicted_future_dates.reset_index()

    # FORMAT: Rename the food names column from 'index' to 'Food Name'
    # Result is a table in this format for each dining hall: "Food Name", 0, 1 , 2
    kins_predicted_dates = kins_predicted_food_dates_reset.rename(columns={'index': 'Food Name'})
    # j2_predicted_dates = j2_predicted_food_dates_reset.rename(columns={'index': 'Food Name'})
    # jcl_predicted_dates = jcl_predicted_food_dates_reset.rename(columns={'index': 'Food Name'})

    # Save these predictions into the database

    # Convert all columns with date values (except 'Food Name') to datetime objects
    for col in kins_predicted_dates.columns[1:]:  # Skip 'Food Name'
        kins_predicted_dates[col] = kins_predicted_dates[col].dt.date  # Convert to date object

    # Resetting the index and assigning it as a new column
    kins_predicted_food_dates_reset = kins_predicted_future_dates.reset_index()

    # Rename the food string column from 'index' to 'Food Name'
    kins_predicted_dates = kins_predicted_food_dates_reset.rename(columns={'index': 'Food Name'})

    # Convert all columns with date values (except 'Food Name') to date objects
    for col in kins_predicted_dates.columns[1:]:  # Skip 'Food Name'
        kins_predicted_dates[col] = kins_predicted_dates[col].dt.date

    # Convert the DataFrame to a NumPy array
    kins_predicted_dates_array = kins_predicted_dates.to_numpy()

    kins_predicted_dates_array = kins_predicted_dates_array[:10]
    save_predictions_to_db (kins_predicted_dates_array, cursor, LocationCodesNum.KINS.value)
    # save_predictions_to_db (j2_predicted_dates, cursor, LocationCodesNum.J2.value)
    # save_predictions_to_db (jcl_predicted_dates, cursor, LocationCodesNum.JCL.value)

    # for col in j2_predicted_dates.columns[1:]:  # Skip 'Food Name'
    #     j2_predicted_dates[col] = kins_predicted_dates[col].dt.date  # Convert to date object
    
    # for col in jcl_predicted_dates.columns[1:]:  # Skip 'Food Name'
    #     jcl_predicted_dates[col] = kins_predicted_dates[col].dt.date  # Convert to date object
    
    # Done
    print ("Done making and writing predictions") # not yet committed, though!
