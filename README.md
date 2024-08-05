# Menu Tracker Web App

Displays availability of specific foods from UT Austin Dining Halls. Uses web scraping, website development, and database management. [Link!](https://menu-tracker-btbwf7bufydxbuds.canadacentral-01.azurewebsites.net/) 

### Overview
The web scraping program collects data from UT Austin Dining Hall online menus and stores it into an online database. The web app allows the user to search the database for a food and filter results by type (Date, Mealtime, Location). 

### Motivation
I would often miss the times when my favorite food, brisket, was served at the dining hall. This project was created so that I’ll never miss it again!

### Services Used
* Github
* Azure Web App
* Azure SQL Server
* Azure SQL Database
* Azure Virtual Network
* Python: pyodbc, requests, and BeautifulSoup

## Brief Overview
See OVERVIEW.md for a description of how each service is used in each part.
### Web Scraping
* Get HTML file of webpage
* Extract data
* Store into database
* Automation (Optional)

### Web App
#### Backend
* Use filters to build SQL query
* Pass results of SQL query to frontend
#### Backend Framework
* Define routes
* Respond to received data 
* Render webpages
#### Frontend
* HTML displays content
* CSS styles content
