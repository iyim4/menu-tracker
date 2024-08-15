# Overview
This document provides a detailed description of how each component works. It covers:

* [Web Scraping](#Web-Scraping)
* [Web App](#Web-App)
    * [Frontend](#Frontend)
    * [Backend Framework](#Backend-Framework)
    * [Backend](#Backend)
* [Cloud Services](#Cloud-Services)

UT Menu Tracker uses `requests` to access the dining hall menu webpages, `BeautifulSoup` to extract data from retrieved webpages, and `pyodbc` to connect to the database to store and retrieve data. Run these commands in the terminal to install them.
``` 
pip install -m beautifulsoup4
pip install -m requests
pip install -m pyodbc
```

## Web Scraping

### Get a Dining Hall Menu
Use `requests` to get the HTML file of a dining hall menu webpage using its URL. 
### Scrape the Data
Use `BeautifulSoup` to parse and extract data from webpage. This requires understanding the structure of the target webpage and identifying under which tag or element that the target data is located. Here, the target data is each food name and the mealtime it is served at.
### Store the Data into the Database
Use `pyodbc` to connect and write the data to the database. For every food, it is the food name, date served, mealtimes served, and location served.
### Automate the Web Scraper
I used Windows Task Scheduler to automatically run the web scraping program from my computer on a daily basis.

## Web App

### Frontend
#### HTML Templates
Use HTML Templates, which are HTML files containing placeholders - part of `Jinja2` syntax - for rendering dynamic content, which will be the search results from the backend. Use HTML `<form>` and `<input>` tags to get user input.
#### Design with CSS
Use CSS to change the webpage layout and design. The 'mobile-first approach' is a design technique that optimizes the layout for mobile devices then expands (pun intended) to larger devices. 

### Backend Framework
The backend framework provides a way to connect the backend and the frontend together. It responds to user interaction and renders webpages accordingly.
#### Define Routes 
Use `Flask` to define routes, which are basically different webpages within a website. When a route is accessed, `Flask` will run the specified function, making it easy to customize different responses for each page. 
#### Respond to Received Data 
In a route's specified function, use `Flask` to get arguments from the user’s webpage access request. This will be search input or filters button interaction. Then, send this information to the backend and get the search result data from it.
#### Render Webpages
Use `Flask` to render HTML templates, which replaces `Jinja2` placeholders with search result data.

### Backend
#### Get Search Input and Filters from the Backend Framework
Passed in from the backend framework. Decode filters, which are stored as a bit string. Since there are 7 filters that will either be on or off, I decided to use a bitstring as a compact way to encode them.
#### Use Filters to Build a SQL Query
Create a SQL query string based on the constraints provided by the now-decoded filters. Different combinations can result in different query clauses spanning multiple tables.
#### Pass the Results of the SQL Query to the Frontend
Use `pyodbc` to execute the query and store the results into a data structure. Then pass this result back to the backend framework. 


## Cloud Services

### GitHub 
Version control. Stores a copy of all web scraping and web app files.
### Azure Web App 
Deploys Menu Tracker, making it available on demand. Handles extra installations needed to deploy `Flask` programs in production environments. Connected to GitHub so that the web app is automatically updated after each push.
### Azure SQL Server and Azure SQL Database
Stores data on the cloud so that the app can access it on demand.
### Azure Virtual Network
Connects the app and the database. Allows all requests from Web App to access database.
### Note: Connecting to the SQL Database in Python
Programs use `pyodbc` to connect to the database, which needs to know the database server, database name, username, and password to access the database, as well as a table name to access the actual data. In order to not hard code these into my programs – and thus expose it to the internet on GitHub – Azure Web App provides a feature called environment variables which stores custom values. In addition, since my computer is not within Menu Tracker's Virtual Network, I must manually tell the SQL server to allow my computer to access the database (necessary for testing web app code and running the web scraper).
