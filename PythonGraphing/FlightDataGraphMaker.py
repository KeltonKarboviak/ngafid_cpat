#!/usr/bin/python

import math
import os
import sys
import time
import datetime
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from Airport import Airport
from LatLon import LatLon
from Runway import Runway
from Vector3d import Vector3d

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
         'data' : [],
         'index': -1,
         'label': 'LatLon',
         'units': 'degrees'}
}


airports = {}
approaches = {}
approachID = 0


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
    getAirportData()

    choices = menu()
    headers = []

    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y_%m_%d_%H-%M-%S')
    graphsFolder = './graphs/' + 'AND'.join([parameters[c]['param'] for c in choices])
    resultsFolder = './results'

    os.system('mkdir graphs')          # Make graphs folder if it doesn't exist
    os.system('mkdir ' + graphsFolder) # Make folder within graphs for this query
    os.system('mkdir results')         # Make results folder if it doesn't exist

    firstTime = True
    for filename in files:
        if '.csv' not in filename:
            continue # Skip file if it isn't a .csv
        elif os.path.isfile('%s/results_%s' % (resultsFolder, filename)):
            continue # Skip file if its results have already been calculated
        flight = filename.split('.')[0]
        print 'Generating graph for: %s' % filename

        with open(folder + '/' + filename, 'r') as file:
            clearData()        # Clear the parameters data for next file
            clearApproaches()  # Clear approaches dict
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

        start = findInitialTakeOff()
        analyzeApproach(start)

        makeGraph(choices, flight, graphsFolder)
        outputToCSV(flight, timestamp, resultsFolder)
        resetApproachID()
        print "--------------------------------------------\n"
    print 'Complete!!!'
    
    
'''
Outputs the approach analysis information to a .csv file. The file will be saved to
    ./results/results_flightID.csv, and appended to ./results/query_timestamp.csv
@param flightID string of the current flight ID to write to a CSV file
@param timestamp string of the timestamp when the program started running.
    This will be used as the filename to store the results of all flights for this program run
@param folder string of the folder in which to store the result CSV file
@author: Kelton Karboviak
'''
def outputToCSV(flightID, timestamp, folder):
    with open('%s/query_%s.csv' % (folder, timestamp), 'a') as globalOutput:
        with open('%s/results_%s.csv' % (folder, flightID), 'w') as output:
            header = 'Flight_ID,Approach_ID,Airport_ID,Landing_Start,Landing_End,Landing_Type,Unstable?,F1_Heading,F2_CT,A_IAS,S_VAS\n'
            if os.stat(globalOutput.name).st_size == 0:
                globalOutput.write(header)
            output.write(header)
            for ID, approach in approaches.items():
                lineToWrite = '%s,%d,%s,%d,%d,%s,%s,%s,%s,%s,%s\n' % \
                              (flightID,
                               ID,
                               approach['airport-code'],
                               approach['landing-start'],
                               approach['landing-end'],
                               approach['landing-type'],
                               'Y' if len(approach['unstable']) > 0 else 'N',
                               "-" if len(approach['F1']) == 0 else sum(approach['F1'])/len(approach['F1']),
                               "-" if len(approach['F2']) == 0 else sum(approach['F2'])/len(approach['F2']),
                               "-" if len(approach['A'])  == 0 else sum(approach['A'])/len(approach['A']),
                               "-" if len(approach['S'])  == 0 else sum(approach['S'])/len(approach['S']))
                globalOutput.write(lineToWrite)
                output.write(lineToWrite)
            # end for
        # end with
    # end with

                         
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
Function clears the contents of the approaches dictionary
@author: Kelton Karboviak
'''
def clearApproaches():
    for key in approaches.keys():
        del approaches[key]


'''
This function will find the initial takeoff and return the first time value after the initial takeoff
@return the first time index after the initial takeoff
'''
def findInitialTakeOff():
    i = 0
    airplaneMSL = parameters[1]['data'][i]
    airplanePoint = parameters[12]['data'][i]
    airport = detectAirport(airplanePoint)
    hAGL = airplaneMSL - airport.alt
    while hAGL < 500 and i < len(parameters[0]['data']):
        airplaneMSL = parameters[1]['data'][i]
        hAGL = airplaneMSL - airport.alt
        i += 1
    return i


'''
This function will reset the approachID to 0 on the start of a new flight.
@author Wyatt Hedrick, Kelton Karboviak
'''
def resetApproachID():
    global approachID
    approachID = 0


'''
This function will return a unique approachID for each approach in the flight.
@returns aID the unique approachID associated with the approach.
@author Wyatt Hedrick, Kelton Karboviak
'''
def getApproachID():
    global approachID
    aID = approachID
    approachID += 1
    return aID


'''
This function analyzes the flight data.
So far we have implemented a check for full stops.
@param startingIndex the time index after the initial takeoff
@author: Wyatt Hedrick, Kelton Karboviak
'''
def analyzeApproach(startingIndex):
    EARTH_RADIUS_MILES = 3959 # Radius of the earth in miles
    i = startingIndex
    while i < len(parameters[0]['data']):
        airplaneMSL = parameters[1]['data'][i]
        airplanePoint = parameters[12]['data'][i]

        airport = detectAirport(airplanePoint)
        distance = airplanePoint.distanceTo(airport.centerLatLon, EARTH_RADIUS_MILES)
        hAGL = airplaneMSL - airport.alt

        if (distance < 1 and hAGL < 500):
            print "Airplane is approaching %s, %s" % (airport.city, airport.state)
            thisApproachID = getApproachID()
            approaches[thisApproachID] = {}
            approaches[thisApproachID]['unstable'] = []
            temp_list = []
            while hAGL > 150 and hAGL < 500:
                i += 1
                airplaneMSL = parameters[1]['data'][i]
                hAGL = airplaneMSL - airport.alt
            # end while

            start = i

            airplaneHdg = parameters[4]['data'][i]
            airplanePoint = parameters[12]['data'][i]

            runway = detectRunway(airplanePoint, airplaneHdg, airport)
            unstableReasons = [ [], [], [], [] ]  # F1, F2, A, S
            while distance < 1 and hAGL <= 150 and hAGL >= 50:
                airplaneHdg = parameters[4]['data'][i]
                airplaneIAS = parameters[2]['data'][i]
                airplaneVAS = parameters[3]['data'][i]

                if runway is not None:
                    cond_F1 = 180 - abs(abs(runway.magHeading - airplaneHdg) - 180) <= 10 
                    cond_F2 = abs(crossTrackToCenterLine(airplanePoint, runway)) <= 50
                else:
                    cond_F1 = cond_F2 = True
                cond_A = airplaneIAS >= 55 and airplaneIAS <= 75
                cond_S = airplaneVAS >= -1000
                if not cond_F1 or not cond_F2 or not cond_A or not cond_S:
                    print "F1=%s, F2=%s, A=%s, S=%s" % (cond_F1, cond_F2, cond_A, cond_S)
                    if not cond_F1:
                        print "\tRunway Heading: %s" % runway.magHeading
                        print "\tAirplane Heading: %s" % airplaneHdg
                        unstableReasons[0].append(airplaneHdg)
                    if not cond_F2:
                        print "\tCrossTrackToCenterLine: %s" % crossTrackToCenterLine(airplanePoint, runway)
                        unstableReasons[1].append( crossTrackToCenterLine(airplanePoint, runway) )
                    if not cond_A:
                        print "\tIndicated Airspeed: %s knots" % (airplaneIAS)
                        unstableReasons[2].append(airplaneIAS)
                    if not cond_S:
                        print "\tVertical Airspeed: %s ft/min" % (airplaneVAS)
                        unstableReasons[3].append(airplaneVAS)
                    temp_list.append(i)
                elif len(temp_list) > 0:
                    approaches[thisApproachID]['unstable'].append( (temp_list[0], temp_list[-1]) )
                    del temp_list[:]
                i += 1

                airplaneMSL = parameters[1]['data'][i]
                airplanePoint = parameters[12]['data'][i]
                distance = airplanePoint.distanceTo(airport.centerLatLon, EARTH_RADIUS_MILES)
                hAGL = airplaneMSL - airport.alt
            # end while

            end = start if start == i else i - 1

            if len(temp_list) > 0:
                approaches[thisApproachID]['unstable'].append( (temp_list[0], temp_list[-1]) )
            
            approaches[thisApproachID]['F1'] = unstableReasons[0]
            approaches[thisApproachID]['F2'] = unstableReasons[1]
            approaches[thisApproachID]['A']  = unstableReasons[2]
            approaches[thisApproachID]['S']  = unstableReasons[3]
            
            i = analyzeLanding(end, airport, thisApproachID)
        # end if

        i += 15
    # end while


'''
This function uses the parameters chosen by the user and graphs
    the time-series data.
It also makes vertical highlights for the regions where unstable approaches and landings were found.
The graphs are then generated as .png files and saved to the passed in folder name
    within the graphs/ folder.
@param: choices the parameters to graph
@param: flightID the ID of the flight being graphed
@param: folder the folder name to save the .png file
@author: Wyatt Hedrick, Kelton Karboviak
'''
def makeGraph(choices, flightID, folder):
    fig, ax =  plt.subplots()
    axes = [ax]
    axes[0].set_xlabel('Time (minutes)')

    title = 'Time vs %s for Flight: %s'
    msg = parameters[choices[0]]['label']
    for i in range(1, len(choices)):  # Loop to add y-axes & append onto msg
        axes.append(axes[0].twinx())
        msg += ' & ' + parameters[choices[i]]['label']
        if i > 1:
            # Move the last y-axis spine over to the right by 10% of the width of the axes
            axes[-1].spines['right'].set_position(('axes', 1 + (.1 * (i-1))))

            # To make the border of the right-most axis visible, we need to turn the frame
            # on. This hides the other plots, however, so we need to turn its fill off.
            axes[-1].set_frame_on(True)
            axes[-1].patch.set_visible(False)

    if len(choices) > 2:
        # Make some space on the right side for the extra y-axis.
        fig.subplots_adjust(right=(0.75))

    COLORS = ('blue', 'red', 'green', 'indigo', 'magenta', 'lightskyblue', 'black', 'salmon', 'chartreuse', 'maroon', 'crimson')

    for ax, c, color in zip(axes, choices, COLORS):
        ax.plot(parameters[0]['data'], parameters[c]['data'], color)
        ax.set_ylabel( '%s (%s)' % (parameters[c]['label'], parameters[c]['units']), color=color )
        ax.tick_params(axis='y', colors=color)

    patches = []
    types = ('Stop and Go', 'Touch and Go', 'Go Around', 'Unstable Approach')
    COLORS = ('lime', 'cyan', 'orange', 'red')

    for landingType, color in zip(types, COLORS):
        patches.append(mpatches.Patch(color=color, label = landingType))
    for key, a in approaches.items():
        for x in a['unstable']:
            axes[0].axvspan( parameters[0]['data'][x[0]], parameters[0]['data'][x[1]], alpha = 0.8, color='red')
        if (a['landing-type'] == 'stop-and-go'):
            landingColor = 'lime'
        elif (a['landing-type'] == 'touch-and-go'):
            landingColor = 'cyan'
        else:
            landingColor = 'orange'
        axes[0].axvspan( parameters[0]['data'][a['landing-start']], parameters[0]['data'][a['landing-end']], alpha = 0.8, color = landingColor)


    plt.title(title % (msg, flightID))

    plt.figlegend(handles=patches, labels=types, loc='center right')

    figure = plt.gcf()
    figure.set_size_inches(25.6, 16)
    plt.savefig('%s/%s.png' % (folder, flightID), dpi = 100)
    plt.clf()


'''
This function detects the airport that is closest to the passed in coordinates.
It performs this by scanning the airportData dictionary and calculating which
    airport as the lowest total difference between lat/lon.
@param: lat the latitude of the plane
@param: lon the longitude of the plane
@author: Wyatt Hedrick
'''
def detectAirport(airplanePoint):
    ourAirport = None
    closestDifference = 0
    for key, airport in airports.items():
        dLat = abs(airport.centerLatLon.lat - airplanePoint.lat) # getting difference in lat and lon
        dLon = abs(airport.centerLatLon.lon - airplanePoint.lon)
        totalDifference = dLat + dLon # adding the differences so we can compare and see which airport is the closest
        if ourAirport is None or totalDifference < closestDifference: # if it is the first time or we found a closer airport
            ourAirport = airport
            closestDifference = totalDifference
    # end for
    return ourAirport


'''
This function will detect the runway that the airplane is going to attempt to land at.
@param: airplaneLat the latitude of the airplane
@param: airplaneLon the longitude of the airplane
@param: airplaneHdg the heading of the heading
@param: airport the airport object that represents the closest airport to the airplane
@returns: the runway object representing the runway the airplane is attempting to land on
@author: Wyatt Hedrick, Kelton Karboviak
'''
def detectRunway(airplanePoint, airplaneHdg, airport):
    ourRunway = None
    closestDifference = 0
    for runway in airport.runways:
        if 180 - abs(abs(runway.magHeading - airplaneHdg) - 180) <= 20:
            dLat = abs(runway.centerLatLon.lat - airplanePoint.lat) # getting difference in lat and lon
            dLon = abs(runway.centerLatLon.lon - airplanePoint.lon)
            totalDifference = dLat + dLon
            if ourRunway is None or totalDifference < closestDifference:
                ourRunway = runway
                closestDifference = totalDifference
    # end for
    return ourRunway


'''
This function calculates the distance the airplane is from the center line in feet based on the passed in coordinates of the airplane and the runway the plane is attempting to land at.

GIS Mapping Tool for verification: http://gistools.igismap.com/bearing

@param: airplaneLat the latitude of the airplane
@param: airplaneLon the longitude of the airplane
@param: runway the runway object representing the closest runway to the airplane
@returns: the distance in feet between the airplane and the center line of the runway
@author: Wyatt Hedrick, Kelton Karboviak
'''
def crossTrackToCenterLine(airplanePoint, runway):
    EARTH_RADIUS_FEET = 20900000  # Radius of the earth in feet
    return airplanePoint.crossTrackDistanceTo(runway.centerLatLon, runway.trueHeading, EARTH_RADIUS_FEET)


'''
This function will analyze the time after the final approach and before the plane reaches a height of 150 feet (or until the flight ends if it is the final landing).
@param: start the time index when the approach ends and the landing begins.
@param: airport the airport that the airplane is attempting to land at
@author: Wyatt Hedrick
'''
def analyzeLanding(start, airport, thisApproachID):
    i = start
    airplaneMSL = parameters[1]['data'][i]
    hAGL = airplaneMSL - airport.alt
    fullStop = False
    elevations = []
    deltaElevation = 6

    fullStop = touchAndGo = False

    while hAGL < 500 and i < len(parameters[0]['data']) - 1:
        airplaneIAS = parameters[2]['data'][i]
        if (not fullStop):
            if airplaneIAS <= 35:
                fullStop = True
            elif deltaElevation <= 5:
                touchAndGo = True
        i += 1
        airplaneMSL = parameters[1]['data'][i]
        hAGL = airplaneMSL - airport.alt
        if len(elevations) < 5:
            elevations.append(hAGL)
        else:
            elevations.pop(0)
            elevations.append(hAGL)
            deltaElevation = sum(elevations)/len(elevations)
    end = i

    if fullStop:
        approaches[thisApproachID]['landing-type'] = 'stop-and-go'
        print "Full Stop!!!!"
    elif touchAndGo:
        approaches[thisApproachID]['landing-type'] = 'touch-and-go'
        print "Touch and Go!!!!"
    else:
        approaches[thisApproachID]['landing-type'] = 'go-around'
        print "Go Around?!?!?!"
        
    approaches[thisApproachID]['airport-code'] = airport.code
    approaches[thisApproachID]['landing-start'] = start
    approaches[thisApproachID]['landing-end'] = end
    print ""
    return end


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
