import csv
from os import name
import sys
import requests
import psycopg2
import tkinter as tk
from urllib.parse import urlparse
from bs4 import BeautifulSoup

vehicleSize=0
manuSize=0
modelSize=0
dimSize=0
engineSize=0
transmissionSize=0

conn = psycopg2.connect(
    host="localhost",
    database="cars_db",
    user="postgres",
    password="password"
)

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
    def __init__(self, make, model, price, year, length, width, height, cylinderCount, horsepower, isElectric, gearNum, manOrAuto):
        self.make = make
        self.model = model
        self.price = price
        self.year = year
        self.length = length
        self.width = width
        self.height = height
        self.cylinderCount = cylinderCount
        self.horsepower = horsepower
        self.isElectric = isElectric
        self.gearNum = gearNum
        self.manOrAuto = manOrAuto

#dictionaries for storing scraped vehicle data and ensuring 3NF in the psql db
manufacturer_dict= {}
model_dict= {}
size_dict= {}
engine_dict= {}
transmission_dict= {}

def scrape_model_data(model, make, year):
    global vehicleSize
    vehicleSize += 1
    #formatting for make. edge cases for replaceing - with " " and capitalizing the first letter of each word. ex: "land-rover" becomes "Land Rover"
    make = make.replace("-", " ").title()
    #edge cases for situations where the make is a single word and should be capitalized.
    if make in ['Bmw', 'Fiat', "Gmc", "Hummer", "Mini"]:
        make = make.upper()
    #edge case for "Am General", correction to "AM General"
    if make== 'Am General':
        make=make.replace('m', 'M')

    #model of car formatted as <h1><b>{year} {make} {model}</b></h1>
    name = model.select_one('h1 b').text.strip()
    #remove the year and make from the name string.
    cleaned = name.replace(f"{year} ", "").replace(f"{make}", "").strip()

    #engine
    if model.select_one('h2:-soup-contains("engine")'):
        cylinderCount = model.select_one('h4:-soup-contains("Cylinders")')
        horsepower = model.select_one('h4:-soup-contains("Horsepower")')
        
        isElectric = model.select_one('h4:-soup-contains("Engine type")')
        cylinderCount = cylinderCount.find_next_sibling(string=True).strip() if cylinderCount else None
        horsepower = horsepower.find_next_sibling(string=True).strip() if horsepower else None
        horsepower = horsepower.replace(" hp", "").strip() if horsepower else None
        isElectric = isElectric.find_next_sibling(string=True).strip() if isElectric else None
        if isElectric in ("electric", "hybrid"):
            isElectric = True
        else:
            isElectric = False
    else:
        cylinderCount = None
        horsepower = None
        isElectric = None

    #size
    if model.select_one('h2:-soup-contains("exterior dimensions")'):
        #each dimension formatted as <h4>{dimension}</h4>\n {value} in.<br />
        length= model.select_one('h4:-soup-contains("Length")')
        width= model.select_one('h4:-soup-contains("Width")')
        height= model.select_one('h4:-soup-contains("Height")')
        length = length.find_next_sibling(string=True).strip() if length else None
        width = width.find_next_sibling(string=True).strip() if width else None
        height = height.find_next_sibling(string=True).strip() if height else None
        #remove " in." from the end of each dimension value
        length = length.replace(" in.", "") if length else None
        width = width.replace(" in.", "") if width else None
        height = height.replace(" in.", "") if height else None
        
    else:
        length = None
        width = None
        height = None

    #transmission data is formatted as <h4>Transmission</h4>\n Transmission, {gearNum}-speed {manOrAuto(boolean)}, Unwanted text<br />
    transmission = model.select_one('h4:-soup-contains("Transmission")')
    gearNum= None

    dctKeywordCount= 0
    splitTrasmCount = 0
    if transmission:
        transmission = transmission.find_next_sibling(string=True).strip()
        #parsing is not consistent between pages, scan through the string to extract the relevant information (i.e "5", "Automatic")
        transmission = transmission.lower()
        for word in transmission.replace("-speed", "").replace("-spd", "").replace("(", "").replace(")", "").split():
            print(f"Processing word: {word}")

            if word=="dual" or word=="clutch":
                dctKeywordCount += 1

            if word=="front" or word=="rear":
                splitTrasmCount += 1

            if word.isdigit():
                gearNum = int(word)

                #true= auto, false= manual
            elif (word == "automatic" or word == "auto/man" or word== "auto" or word == "dual-clutch" or word == "dct"
                  or word== "auto-shift" or word== "sportshift" or word== "tronic" or word== "tiptronic"or word=="stronic"
                  or word=="quickshift" or word=="steptronic" or dctKeywordCount == 2 or splitTrasmCount == 2):
                manOrAuto = True
                dctKeywordCount = 0
                splitTrasmCount = 0
                
            elif word == "manual" or word == "man":
                manOrAuto = False
    else:
        gearNum = None
        manOrAuto = False

    #price is formatted as <div class="estimated-cost"> estimated cost $XX,XXX</div>
    price = model.select_one('.estimated-cost')
    #remove "estimated cost: " and "$" from string
    if price:
        price = price.text.replace("estimated cost ", "").replace("$", "").replace(",", "").strip()

    scraped_vehicle = Vehicle(make, cleaned, price, year, length, width, height, cylinderCount, horsepower, isElectric, gearNum, manOrAuto)
    return scraped_vehicle

def on_button_click(): 
    #iterate through make and year arrays to build url for individual models
    #formatted as https://www.carspecs.us/cars/{year}/{make}
    for make in make_array:
        #check for every year which makes have produced a model.
        #years in HTML are formatted as <li><a href="/cars/{year}/{make}/">{year}</a></li>
        year_array = []
        year_request = requests.get(f"https://www.carspecs.us/cars/{make}")
        year_soup = BeautifulSoup(year_request.text, 'html.parser')
        #avoid error throeing from requests. urls that don't exist will return a 404 error. many makes will not have models made in certain years.
        for year in range(2010, 2026):
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
                save_to_db(scraped_vehicle)
                print(f"Finished processing model: {model_url}")

def save_to_db(scraped_vehicle):
    #if the make is not already in the dictionary, add it
    if scraped_vehicle.make not in manufacturer_dict:
        manufacturer_dict[scraped_vehicle.make] = {}
        global manuSize
        manuSize += 1
        manufacturer_dict[scraped_vehicle.make]= manuSize

    if scraped_vehicle.model not in model_dict:
        model_dict[scraped_vehicle.model] = {}
        global modelSize
        modelSize += 1
        model_dict[scraped_vehicle.model]= modelSize

    size_key = (scraped_vehicle.length, scraped_vehicle.width, scraped_vehicle.height)
    if size_key not in size_dict:
        size_dict[size_key] = {}
        global dimSize
        dimSize += 1
        size_dict[size_key] = dimSize

    engine_key = (scraped_vehicle.cylinderCount, scraped_vehicle.horsepower, scraped_vehicle.isElectric)
    if engine_key not in engine_dict:
        engine_dict[engine_key] = {}
        global engineSize
        engineSize += 1
        engine_dict[engine_key] = engineSize

    #each combination of gearNum and manOrAuto is stored as a key in transmission_dict
    if scraped_vehicle.manOrAuto is not None:
        transmission_key = (scraped_vehicle.gearNum, scraped_vehicle.manOrAuto)
        if transmission_key not in transmission_dict:
            transmission_dict[transmission_key] = {}
            global transmissionSize
            transmissionSize += 1
            transmission_dict[transmission_key] = transmissionSize
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT current_database(), inet_server_port();")
        
        #query to manufacturer db, model is dependant, and therefore vehicle
        cursor.execute(
            "INSERT INTO manufacturer (makeid, mfname) VALUES (%s, %s) ON CONFLICT (makeid) DO NOTHING",
            (manufacturer_dict[scraped_vehicle.make], scraped_vehicle.make)
        )

        #model query
        cursor.execute(
            "INSERT INTO model (modelid, modelname) VALUES (%s, %s) ON CONFLICT (modelid) DO NOTHING",
            (model_dict[scraped_vehicle.model], scraped_vehicle.model)
        )

        #size query
        cursor.execute(
            "INSERT INTO size (sizeid, length, width, height) VALUES (%s, %s, %s, %s) ON CONFLICT (sizeid) DO NOTHING",
            (size_dict.get(size_key, None) if 'size_key' in locals() else None, scraped_vehicle.length, scraped_vehicle.width, scraped_vehicle.height)
        )

        #engine query
        cursor.execute(
            "INSERT INTO engine (engineid, cylinderCount, horsepower, isElectric) VALUES (%s, %s, %s, %s) ON CONFLICT (engineid) DO NOTHING",
            (engine_dict.get(engine_key, None) if 'engine_key' in locals() else None, scraped_vehicle.cylinderCount, scraped_vehicle.horsepower, scraped_vehicle.isElectric)
        )

        #transmission query
        cursor.execute(
            "INSERT INTO transmission (transmid, gearNum, manOrAuto) VALUES (%s, %s, %s) ON CONFLICT (transmid) DO NOTHING",
            (transmission_dict.get(transmission_key, None) if 'transmission_key' in locals() else None, scraped_vehicle.gearNum, scraped_vehicle.manOrAuto)
        )

        #final query, adds vehcile id to db with associated foriegn keys from dictionaries
        cursor.execute(
            "INSERT INTO vehicle (vehicleid, modelid, engineid, sizeid, transmid, price, year) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (vehicleid) DO NOTHING",
            (vehicleSize, model_dict[scraped_vehicle.model], engine_dict.get(engine_key, None) if 'engine_key' in locals() else None, size_dict.get(size_key,
            None) if 'size_key' in locals() else None, transmission_dict.get(transmission_key, None) if 'transmission_key' in locals() else None
            , scraped_vehicle.price, scraped_vehicle.year)
        )
        conn.commit()
        print(f"Saved data for {scraped_vehicle.year} {scraped_vehicle.make} {scraped_vehicle.model} to DB.")
    except psycopg2.Error as e:
        print(f"Error saving data to database: {e}")
        #terminate program
        sys.exit(1)
    finally:
        if 'cursor' in locals():
            cursor.close()

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
