# Overview
This document describes how each service is used in the app.

* Github
* Azure Web App
* Azure SQL Server
* Azure SQL Database
* Azure Virtual Network
* Python: `pyodbc`, `requests`, and `BeautifulSoup`

## Cloud Services
### GitHub 
Version control. Stores all files.
### Azure Web App 
Deploys app. Handles extra installations needed to deploy `Flask` programs in production environments. Connected to GitHub so that the website is automatically updated after each push.
### Azure SQL Server
Used to host SQL database. Unsure of exact usage
### Azure SQL Database
Stores data.
### Azure Virtual Network
Connects app and database. Allows all requests from Web App to access database.
### Connecting to the SQL Database in Python
Programs use `pyodbc` to connect to the database. It needs to know the database server, database name, username, and password to access the database, and a table name to access the actual data. In order to not hard code these into my program – and thus expose it to the internet on GitHub – Azure Web App provides a feature called environment variables which stores custom values


## Web Scraping
* Get HTML file of webpage
* Extract Data
* Store into the Database
* Automation (Optional)

Requires `requests` to access a webpage, `BeautifulSoup` to extract data from webpage, and  `pyodbc` to connect to the database. Run this in the terminal to install them.
``` sh
pip install -m beautifulsoup4
pip install -m requests
pip install -m pyodbc
```
### Get HTML file of webpage
Use `requests` to get the HTML file of a webpage using its URL. 
### Extract Data
Use `BeautifulSoup` to parse and extract data from webpage. This requires understanding the structure of the target webpage: under which tag or element the target data is located.
### Store into the Database
Use `pyodbc` to connect and write data to the database
### Automation (Optional)
I used Windows Task Scheduler to run the web scraping program from my computer on a daily basis, without the need for human interaction. 


## Web App
TODO finish writing

Requires `Flask` and `pyodbc`
### Backend
Retrieves data from database.
* Use filters to build SQL query
* Pass results of SQL query to frontend

#### Use filters to build SQL query
To extract data from database, use `pyodbc` to execute SQL queries. Filters is a parameter passed in from the front end. Create a query based on the constraints provided by filters. 
#### Pass results of SQL query to frontend
Use `pyodbc` to execute the query and store the results into a data structure. Then pass this result to the backend framework, `Flask`, which provides methods to get it on the frontend.
### Backend Framework
Backend framework provides a way to connect the backend and frontend together. It responds to user interaction and renders webpages accordingly.
* Define routes
* Respond to received data 
* Render webpages

#### Define routes 
Use `Flask` to define routes, which are basically different webpages within a website. This makes a specified function in the code run when that route is accessed.
#### Respond to received data 
In that specified function, use `Flask` to get arguments from the user’s webpage access request. This will be search input or filters button interaction
#### Render webpages
Use `Flask` to render templates, which are HTML files with placeholder for dynamic content, i.e. variables. It uses the Jinja2 engine to produce the final HTML file that will be used.
### Frontend
This is what the users see.
* HTML displays content
* CSS styles content
#### HTML displays content
An HTML file contains the content that a webpage displays. It also provides a way to send have user input to the website, which will be sent to the backend framework and processed there.
#### CSS styles content	
CSS changes the look of the content
