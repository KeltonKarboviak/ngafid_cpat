#!/usr/bin/python

import os
import sys
import time
import datetime
from FlightAnalysis import FlightAnalyzer
from FlightGraphing import FlightGrapher
from LatLon import LatLon
from Airport import Airport
from Runway import Runway

parameters = {
    0: {'param': 'time',
        'data' : [],
        'index': -1,
        'label': 'Time',
        'units': 'minutes'},
    1: {'param': 'msl_altitude',
        'data' : [],
        'index': -1,
        'label': 'Altitude',
        'units': 'ft'},
    2: {'param': 'indicated_airspeed',
        'data' : [],
        'index': -1,
        'label': 'Airspeed',
        'units': 'kts'},
    3: {'param': 'vertical_airspeed',
        'data' : [],
        'index': -1,
        'label': 'Vertical Airspeed',
        'units': 'kts'},
    4: {'param': 'heading',
        'data' : [],
        'index': -1,
        'label': 'Heading',
        'units': 'degrees'},
    5: {'param': 'pitch_attitude',
        'data' : [],
        'index': -1,
        'label': 'Pitch Attitude',
        'units': 'degrees'},
    6: {'param': 'roll_attitude',
        'data' : [],
        'index': -1,
        'label': 'Roll Attitude',
        'units': 'degrees'},
    7: {'param': 'eng_1_rpm',
        'data' : [],
        'index': -1,
        'label': 'Engine RPM',
        'units': 'rpm'},
    8: {'param': 'vertical_acceleration',
        'data' : [],
        'index': -1,
        'label': 'Vertical Acceleration',
        'units': 'ft/s^2'},
    9: {'param': 'groundspeed',
        'data' : [],
        'index': -1,
        'label': 'Groundspeed',
        'units': 'kts'},
    10: {'param': 'latitude',
        'data' : [],
        'index': -1,
        'label': 'Latitude',
        'units': 'degrees'},
    11: {'param': 'longitude',
        'data' : [],
        'index': -1,
        'label': 'Longitude',
        'units': 'degrees'},
    12: {'param': 'LatLon',
        'data': [],
        'index': -1,
        'label': 'LatLon',
        'units': 'degrees'}
}

airports = {}

'''
Function clears the contents of each sub-list in the passed in list.
It does not delete the sub-lists themselves.
For example, after this function: data = [ [], [], ... ]
This happens by reference so data does not need to be returned.
@author: Kelton Karboviak
'''
def clearData():
    for key in parameters.keys():
        del parameters[key]['data'][:]

'''
Main function gets a list of all the files contained within the passed in
    folder name. Then scans through each file one-by-one in order to pass it
    to the analyze data function to find approaches and landings.
After the data is analyzed, it then calls makeGraph to create the graph image.
@author: Wyatt Hedrick, Kelton Karboviak
'''
def main(argv):
    if len(argv) != 1:
        print '''
#####################################
#                                   #
#  ./FlightDataGraphMaker <folder>  #
#                                   #
#####################################
'''
        exit()

    folder = argv[0]
    files = os.listdir(folder)

    choices = menu()
    headers = []

    getAirportData()

    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y_%m_%d_%H-%M-%S')
    graphsFolder = './graphs/' + 'AND'.join([parameters[c]['param'] for c in choices])
    resultsFolder = './results'
    Analyzer = FlightAnalyzer(timestamp, resultsFolder, airports)
    Grapher = FlightGrapher(choices, graphsFolder)

    os.system('mkdir graphs')          # Make graphs folder if it doesn't exist
    os.system('mkdir ' + graphsFolder) # Make folder within graphs for this query
    os.system('mkdir results')         # Make results folder if it doesn't exist

    firstTime = True
    for filename in files:
        if '.csv' not in filename:
            continue # Skip file if it isn't a .csv
        elif os.path.isfile('%s/results_%s' % (resultsFolder, filename)):
            continue # Skip file if it's results have already been calculated
        flight = filename.split('.')[0]
        print 'Generating graph for: %s' % filename

        with open(folder + '/' + filename, 'r') as file:
            clearData()        # Clear the parameters data for next file
            for x in range(9):    # First 9 lines are garbage
                file.readline()
            if firstTime:         # If this is first time, get the data headers (line 10)
                headers = file.readline().split(', ')
                for key, param in parameters.items(): # Find the corresponding header index for each label
                    try:
                        param['index'] = headers.index( param['param'] )
                    except ValueError, e: continue
                firstTime = False
            else:
                file.readline()

            for line in file:
                row = line.split(', ')
                parameters[0]['data'].append( float(row[parameters[0]['index']]) / 60000 ) # Add time value
                for key, param in parameters.items(): # Add rest of param values (everything but time)
                    if key != 0 and key != 12:
                        param['data'].append( float(row[param['index']]) )
                parameters[12]['data'].append( LatLon(parameters[10]['data'][-1], parameters[11]['data'][-1]) )
                # end for

        approaches = Analyzer.analyze(flight, parameters)
        Grapher.graph(flight, parameters, approaches)
        print "--------------------------------------------\n"
    print 'Complete!!!'

'''
Populate a dictionary containing airport data for all airports throughout the U.S.
@author: Wyatt Hedrick
'''
def getAirportData():
    with open('./Airports.csv', 'r') as file:
        file.readline() # Trash line of data headers
        for line in file:
            row = line.split(',')
            #             code,   name,   city,  state,      latitude,     longitude,      altitude
            a = Airport(row[0], row[1], row[2], row[3], float(row[4]), float(row[5]), float(row[6]))
            airports[row[0]] = a # Insert into airports dict with airportCode as key

    with open ('./AirportsDetailed.csv', 'r') as file:
        file.readline() # Trash line of data headers
        for line in file:
            row = line.split(',')
            #     airportCode,      altitude, runwayCode,      magHdg,        trueHdg,      centerLat,      centerLon
            r = Runway(row[2], float(row[6]), row[10], float(row[11]), float(row[12]), float(row[25]), float(row[26]))
            airports[row[2]].addRunway(r) # Add runway to corresponding airport

'''
This function prints out a menu to the user for them to select parameters to graph.
@return: a list of the options (1-11) the user chose
@author: Wyatt Hedrick, Kelton Karboviak
'''
def menu():
    print '''
1. MSL Altitude
2. Indicated Airspeed
3. Vertical Airspeed
4. Heading
5. Pitch Attitude
6. Roll Attitude
7. Engine 1 RPM
8. Vertical Acceleration
9. Groundspeed
10. Latitude
11. Longitude
'''

    choices = []
    choice = -1

    while choice < 1 or choice > 11:
        choice = input('Which attribute for y1? ')
    choices.append(choice)

    counter = 1
    while counter < 11 and choice != 0:
        choice = input('(optional -- enter 0 to opt out) which attribute for y%d? ' % (counter+1))
        if (choice not in choices) and (choice > 1 and choice < 11):
            choices.append(choice)
            counter += 1

    return choices


'''
This checks to see if the program is being run directly via command-line. If it is, then it calls
    the main function passing in the command-line arguments
    # TODO Implement a command-line flag to have the program profile this program's run-time stats
'''
if __name__ == "__main__":
    main(sys.argv[1:])
