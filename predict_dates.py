from datetime import datetime
from searchdb import MEALTIME_CODES, LOCATION_CODES 

def predict_future_date (food_name: str) -> datetime:
  """  """
  # print ("in predict future date")

  predicted_date = datetime (2025, 2, 24).strftime("%d %B '%y").lstrip('0')
  predicted_date_entry = [predicted_date, MEALTIME_CODES[1], LOCATION_CODES[1]]
  print(f"todo implement. returning dummy value: {predicted_date_entry}")

  return predicted_date_entry
