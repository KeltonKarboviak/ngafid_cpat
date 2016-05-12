#!/usr/bin/python

import os
import sys
import time
import datetime
import MySQLdb
from FlightAnalysis import FlightAnalyzer
#from FlightGraphing import FlightGrapher
from LatLon import LatLon
from Airport import Airport
from Runway import Runway

parameters = {
    0: {'param': 'time',
        'data' : [],
        'label': 'Time',
        'units': 'minutes'},
    1: {'param': 'msl_altitude',
        'data' : [],
        'label': 'Altitude',
        'units': 'ft'},
    2: {'param': 'indicated_airspeed',
        'data' : [],
        'label': 'Airspeed',
        'units': 'kts'},
    3: {'param': 'vertical_airspeed',
        'data' : [],
        'label': 'Vertical Airspeed',
        'units': 'kts'},
    4: {'param': 'heading',
        'data' : [],
        'label': 'Heading',
        'units': 'degrees'},
    10: {'param': 'latitude',
        'data' : [],
        'label': 'Latitude',
        'units': 'degrees'},
    11: {'param': 'longitude',
        'data' : [],
        'label': 'Longitude',
        'units': 'degrees'},
    12: {'param': 'LatLon',
        'data': [],
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
def main(db, argv):
    cursor = db.cursor(MySQLdb.cursors.DictCursor)

    # If there are no flight_ids passed as command-line args,
    # fetch all flights that haven't been analyzed for approaches yet
    # Otherwise the ids passed into argv will only be analyzed
    if len(argv) == 0:
        fetchFlightsSQL = "SELECT flight_id FROM flight_analyses WHERE approach_analysis = 0;"
        cursor.execute(fetchFlightsSQL)
        data = cursor.fetchall()
        argv = [datum['flight_id'] for datum in data]

    getAirportData()

    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y_%m_%d_%H-%M-%S')
    # graphsFolder = './graphs/' + 'AND'.join([parameters[c]['param'] for c in choices])
    resultsFolder = './results'
    Analyzer = FlightAnalyzer(db, timestamp, resultsFolder, airports)
    #Grapher = FlightGrapher(choices, graphsFolder)

    # os.system('mkdir graphs')          # Make graphs folder if it doesn't exist
    # os.system('mkdir ' + graphsFolder) # Make folder within graphs for this query
    # os.system('mkdir results')         # Make results folder if it doesn't exist

    fetchDataSQL = "SELECT time, msl_altitude, indicated_airspeed, vertical_airspeed, heading, latitude, longitude " \
                 + "FROM main " \
                 + "WHERE flight = %s;"

    fetchCraftTypeSQL = "SELECT DISTINCT fl.aircraft_type " \
                      + "FROM main as ma, flight_id as fl " \
                      + "WHERE fl.id = %s AND fl.id = ma.flight;"

    for flight_id in argv:
        print "Processing flight_id: ", flight_id
        # check to see if flight exists at all
        # check to see if it exists in approach table yet

        clearData()  # Clear the parameters data for next flight

        # Get the flight's aircraft type
        cursor.execute(fetchCraftTypeSQL, (flight_id,))
        aircraftType = cursor.fetchone()['aircraft_type']

        # Get the flight's data
        cursor.execute(fetchDataSQL, (flight_id,))
        rows = cursor.fetchall()

        for row in rows:
            parameters[0]['data'].append( float(row['time']) / 60000 )  # Add time value
            for key, param in parameters.items():
                if key != 0 and key != 12:
                    param['data'].append( float(row[param['param']]) )
            parameters[12]['data'].append( LatLon(row['latitude'], row['longitude']) )
        # end for

        approaches = Analyzer.analyze(flight_id, aircraftType, parameters)
        #Grapher.graph(flight, parameters, approaches)
        print "Processing Complete!"
        print "--------------------------------------------\n"
    # end for
    print 'Program Run Complete!'

'''
Populate a dictionary containing airport data for all airports throughout the U.S.
@author: Wyatt Hedrick
'''
def getAirportData():
    with open('../data/Airports.csv', 'r') as file:
        file.readline() # Trash line of data headers
        for line in file:
            row = line.split(',')
            #             code,   name,   city,  state,      latitude,     longitude,      altitude
            a = Airport(row[0], row[1], row[2], row[3], float(row[4]), float(row[5]), float(row[6]))
            airports[row[0]] = a # Insert into airports dict with airportCode as key

    with open ('../data/AirportsDetailed.csv', 'r') as file:
        file.readline() # Trash line of data headers
        for line in file:
            row = line.split(',')
            #     airportCode,      altitude, runwayCode,      magHdg,        trueHdg,      centerLat,      centerLon
            r = Runway(row[2], float(row[6]), row[10], float(row[11]), float(row[12]), float(row[25]), float(row[26]))
            airports[row[2]].addRunway(r) # Add runway to corresponding airport


def usage():
        print '''
#####################################
#                                   #
#  ./main <flight_id> [flight_id]+  #
#                                   #
#####################################
'''
        exit()


'''
This checks to see if the program is being run directly via command-line. If it is, then it calls
    the main function passing in the command-line arguments
    # TODO Implement a command-line flag to have the program profile this program's run-time stats
'''
if __name__ == "__main__":

    db = None
    try:
        db = MySQLdb.connect("localhost", "root", "NG@F1D", "dev_fdm_test")
        main(db, sys.argv[1:])
    except MySQLdb.Error, e:
        print "MySQLdb Error [%d]: %s\n" % (e.args[0], e.args[1])
        print "Last Executed Query: ", self.cursor._last_executed
    finally:
        if db is not None: db.close()
