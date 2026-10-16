import csv
import requests
from bs4 import BeautifulSoup

class meeting:
    def __init__(classMeet, name, meetDates, meetTime, isPM):
        classMeet.name= name
        classMeet.meetDates= meetDates
        classMeet.meetTime= meetTime
        classMeet.isPM= isPM

class final:
    def __init__(classMeet, name, finalDay, finalTime):
        classMeet.name= name
        classMeet.finalDay= finalDay
        classMeet.finalTime= finalTime

def convToDayAbbreviation(day):
    if "Monday" in day:
        dayConv='M'
    elif "Tuesday" in day:
        dayConv='T'
    elif "Wednesday" in day:
        dayConv='W'
    elif "Thursday" in day:
        dayConv="TH"
    elif "Friday" in day:
        dayConv="F"
    elif "Saturday" in day:
        dayConv= "S"
    else:
        dayConv="Error"
    return dayConv

def convFinaltimeToInt(row):
    if row.txt[1]== "-" or row.text[1]==":":
        intValue=row.text[0]
    else:
        intValue= row.text[0:2]

def main():

    #requests html code 
    r= requests.get('https://www.unr.edu/admissions/records/academic-calendar/finals-schedule')

    #parses the html text from the requests pull
    soup=BeautifulSoup(r.text, 'html.parser')

    #list for meeting objects
    classes= []

    #opens file with student schedule
    with open('student_classes.txt') as input:
        #iterates thorugh each line, splits class name, meeting dates, etc for meeting object
        for line in input:
            name, meetDates, meetTime,isPM= line.split("/")
            #subdivides meeting dates into its own list
            meetDates= meetDates.split(",")
            #creates new meeting object
            meetInstance= meeting(name,meetDates,meetTime, isPM)
            #adds new meeting object to classes list
            classes.append(meetInstance)

    #list for every table from the HTML
    tableResults=soup.find_all('table')

    #list for completed schedule. used to write to csv
    completedSched=[]

    #compare for each class schedule
    for indiv in classes:
        success=False
        meetDay= indiv.meetDates
        #check each table; day first,then time/ meridiem
        for table in tableResults:
            if success==True:
                break

            day=table.find("caption")
            abbrevDay= convToDayAbbreviation(day.text)
            for indivDay in meetDay:
                if indivDay==abbrevDay:
                    #checks every time in the table
                    tableRows= table.find_all("td")
                    for row in tableRows:

                        if row.text[1]== "-" or row.text[1]==":":
                            intValue=row.text[0]
                        elif ord(row.text[0])<=57 and ord(row.text[0])>=48:
                            intValue= row.text[0:2]
                        else:
                            continue
                        if (int(intValue)<= int(indiv.meetTime)) or (indiv.isPM=='pm'):
                            am="a.m."
                            pm="p.m."
                            if (am in row.text and indiv.isPM=="am") or (pm in row.text and indiv.isPM=='pm'):
                                #case for if the schedule is empty(avoids seg faults)
                                if completedSched==[]:
                                    success= True
                                    finalF= final(indiv.name, abbrevDay, row.text)
                                    completedSched.append(finalF)
                                    break
                                else:
                                    for storedFinals in completedSched:
                                        if storedFinals.finalDay== abbrevDay:
                                            if (indiv.isPM=='pm' and am in row.text) or (indiv.isPM=='am' and pm in row.text):
                                                success= True
                                                finalF= final(indiv.name, abbrevDay, row.text)
                                                completedSched.append(finalF)
                                                break
    #writes all final schedules into csv
    with open('finalSchedule.csv', mode= "w", newline= '\n') as out:
        finalWrite= csv.writer(out, delimiter=',', quotechar='|', quoting=csv.QUOTE_NONE)
        finalWrite.writerow(["Generated", "Final", "Schedule:"])
        finalWrite.writerow(["Class Name","Day of Final","Hours"])
        for indivFinalSched in completedSched:
            finalWrite.writerow([indivFinalSched.name, indivFinalSched.finalDay, indivFinalSched.finalTime])





if __name__ == "__main__":
    main()
