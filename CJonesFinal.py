import csv
from os import name
import requests
import psycopg2
import tkinter as tk
from urllib.parse import urlparse
from bs4 import BeautifulSoup

#arrays for building a url
#one for make and one for year
make_array = ['acura', 'alfa-romeo', 'am-general', 'aston-martin', 'audi', 'bentley', 'bmw', 'bugatti','buick', 'cadillac', 
             'chevrolet', 'chrysler', 'citroen','daewoo','daihatsu','dodge','eagle','ferrari', 'fiat', 'fisker', 'ford', 
             'freightliner','genesis','geo','gmc', 'honda', 'hummer', 'hyundai', 'infiniti', 'international','isuzu', 
             'jaguar', 'jeep', 'kia', 'lamborghini', 'land-rover', 'lexus', 'lincoln', 'lotus', 'lucid','maserati', 'maybach',
             'mazda', 'mclaren', 'mercedes-benz', 'mercury', 'mini', 'mitsubishi', 'morgan', 'nissan', 'oldsmobile', 'panoz', 
             'plymouth', 'pontiac', 'porsche', 'ram', 'rivian','rolls-royce', 'saab', 'saleen', 'saturn', 'scion', 'smart', 
             'spyker', 'subaru', 'suzuki', 'tesla', 'toyota', 'volkswagen', 'volvo']

class Vehicle:
    def __init__(self, make, model, price, year):
        self.make = make
        self.model = model
        self.price = price
        self.year = year

def scrape_model_data(model, make, year):
    #formatting for make. edge cases for replaceing - with " " and capitalizing the first letter of each word. ex: "land-rover" becomes "Land Rover"
    make = make.replace("-", " ").title()
    #edge cases for situations where the make is a single word and should be capitalized.
    if make in ['Bmw', 'Fiat', "Gmc", "Hummer", "Mini"]:
        make = make.upper()
    #edge case fo "Am General", correction to "AM General"
    if make== 'Am General':
        make=make.replace('m', 'M')

    #model of car formatted as <h1><b>{year} {make} {model}</b></h1>
    name = model.select_one('h1 b').text.strip()
    #remove the year and make from the name string.
    cleaned = name.replace(f"{year} ", "").replace(f"{make}", "").strip()

    #price is formatted as <div class="estimated-cost"> estimated cost $XX,XXX</div>
    rice = model.select_one('.estimated-cost')
    #remove "estimated cost: " and "$" from string
    if price:
        price = price.text.replace("estimated cost ", "").replace("$", "").strip()

    scraped_vehicle = Vehicle(make, cleaned, price, year)
    return scraped_vehicle

def on_button_click():
    #try:
        #iterate through make and year arrays to build url for individual models
        #formatted as https://www.carspecs.us/cars/{year}/{make}
        for make in make_array:
            #check for every year which makes have produced a model.
            #years in HTML are formatted as <li><a href="/cars/{year}/{make}/">{year}</a></li>
            year_array = []
            year_request = requests.get(f"https://www.carspecs.us/cars/{make}")
            year_soup = BeautifulSoup(year_request.text, 'html.parser')
            #avoid error throeing from requests. urls that don't exist will return a 404 error. many makes will not have models made in certain years.
            for year in range(1990, 2026):
                #check if the year is in the soup
                if year_soup.find('li', string=str(year)):
                    year_array.append(year)
            for year in year_array:
                valid_urls = []
                url = f"https://www.carspecs.us/cars/{year}/{make}"

                response = requests.get(url)
                #check if url is valid. many makes will not have models made in certain years.
                response.raise_for_status()

                #parses the html content of the page
                soup = BeautifulSoup(response.text, 'html.parser')
                #model section of url is formatted as https://www.carspecs.us/cars/{year}/{make}/{model}
                #structured in html as "<li><a href="/cars/{year}/{make}/{model}/...">{model}</a></li>"
                model_links = soup.select('li a')

                #for each model link, check if the href attribute contains the year and make, then append the full URL to the model_links list
                for link in model_links:
                    print(f"{link}")#debug
                    href = link.get('href')
                    if href and f"/cars/{year}/{make}/" in href:
                        #remove /cars/{year}/{make}/ from string
                        href = href.replace(f"/cars/{year}/{make}", "")
                        valid_urls.append(f"{url}{href}")
    
                #iterate through the model links and scrape the data for each model
                for model_url in valid_urls:
                    print(f"Fetching data from: {model_url}")
                    model_response = requests.get(model_url)
                    model_response.raise_for_status()
                    model_soup = BeautifulSoup(model_response.text, 'html.parser')
                    #scrape the data for each model and save it to a csv file
                    scraped_vehicle= scrape_model_data(model_soup, make, str(year))
                    save_to_csv(scraped_vehicle)

    #except requests.exceptions.RequestException as e:
    #    print(f"Error fetching the URL: {e}")
    #    return
#function for testing requests and beutifulSoup. Should aggregate the data and save it to a csv file,
#which will be replaced with a database in the future
def save_to_csv(scraped_vehicle):
    append_row=[scraped_vehicle.model, scraped_vehicle.price, scraped_vehicle.make, scraped_vehicle.year]
    with open('test.csv', 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        #write the scraped data to the CSV file. add and endline to the end of each row
        writer.writerow(append_row)
        print(f"Saved data for {scraped_vehicle.year} {scraped_vehicle.make} {scraped_vehicle.model} to CSV.")

#program which scrapes data from carspecs.us
#outline for a tool that will be implemented with a GUI and PostgreSQL database in the future
#the data scraping is a one time process
#the GUI will be used to query the database and display the results in a user-friendly manner

#gui implementation
root = tk.Tk()
root.title("Vehicle Database")
# Add GUI elements here
root.geometry("720x480")
label = tk.Label(root, text="Vehicle Database", font=("Helvetica", 24))
label.pack(pady=20)

button = tk.Button(root, text="get data", command=on_button_click)
button.pack(pady=10)
root.mainloop()
