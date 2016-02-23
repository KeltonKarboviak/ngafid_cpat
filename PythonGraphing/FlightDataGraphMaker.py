#!/usr/bin/python

import math
import os
import sys
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
        'units': 'degrees'}
}

exceedances = {
    'stop-and-go' : [],
    'touch-and-go': [],
    'go-around': [],
    'unstable': []
}

airports = {}


'''
Main function gets a list of all the files contained within the passed in
    folder name. Then scans through each file one-by-one in order to pass it
    to the analyze data function to find exceedances.
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

    graphsFolder = './graphs/' + 'AND'.join([parameters[c]['param'] for c in choices])

    os.system('mkdir graphs')          # Make graphs folder if it doesn't exist
    os.system('mkdir ' + graphsFolder) # Make folder within graphs for this query

    firstTime = True
    for filename in files:
        if '.csv' not in filename: continue # Skip file if it isn't a .csv
        flight = filename.split('.')[0]
        print 'Generating graph for: %s' % filename

        with open(folder + '/' + filename, 'r') as file:
            clearData()        # Clear the parameters data for next file
            clearExceedances() # Clear exceedance tuples
            for x in range(9):    # First 9 lines are garbage
                file.readline()
            if firstTime:         # If this is first time, get the data headers (line 10)
                headers = file.readline().split(', ')
                for key in parameters.keys(): # Find the corresponding header index for each label
                    parameters[key]['index'] = headers.index( parameters[key]['param'] )
                firstTime = False
            else:
                file.readline()

            for line in file:
                row = line.split(', ')
                parameters[0]['data'].append( float(row[parameters[0]['index']]) / 60000 ) # Add time value
                for key in parameters.keys(): # Add rest of param values (everything but time)
                    if key != 0:
                        parameters[key]['data'].append( float(row[parameters[key]['index']]) )

        start = findInitialTakeOff()
        analyzeData(start)

        makeGraph(choices, flight, graphsFolder)
        print "--------------------------------------------"
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
            airports[row[0]] = a # Insert into airports dict with airport_code as key

    with open ('./AirportsDetailed.csv', 'r') as file:
        file.readline() # Trash line of data headers
        for line in file:
            row = line.split(',')
            #    airport_code,      altitude, runway_code,     magHdg,        trueHdg,      centerLat,      centerLon
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
Function clears the contents of the exceedances dictionary
@author: Kelton Karboviak
'''
def clearExceedances():
    for key in exceedances.keys():
        del exceedances[key][:]

'''
This function will find the initial takeoff and return the first time value after the initial takeoff
@return the first time index after the initial takeoff
'''
def findInitialTakeOff():
    i = 0
    airplaneMSL = parameters[1]['data'][i]
    airplaneLat = parameters[10]['data'][i]
    airplaneLon = parameters[11]['data'][i]
    airport = detectAirport(airplaneLat, airplaneLon)
    hAGL = airplaneMSL - airport.alt
    while hAGL < 500 and i < len(parameters[0]['data']):
        airplaneMSL = parameters[1]['data'][i]
        hAGL = airplaneMSL - airport.alt
        i += 1
    return i


'''
This function analyzes the flight data.
So far we have implemented a check for full stops.
@param startingIndex the time index after the initial takeoff
@author: Wyatt Hedrick, Kelton Karboviak
    # TODO Implement go-around detection - Kelton
    # TODO Implement touch-and-go detection - Wyatt
    # TODO Implement unstable vs. stable approach detection - Kelton
    # TODO Report each exceedance that occurred (if any) - Wyatt
'''
def analyzeData(startingIndex):
    i = startingIndex
    while i < len(parameters[0]['data']):
        airplaneMSL = parameters[1]['data'][i]
        airplaneLat = parameters[10]['data'][i]
        airplaneLon = parameters[11]['data'][i]

        airport = detectAirport(airplaneLat, airplaneLon)
        distance = haversine(airplaneLat, airplaneLon, airport.lat, airport.lon)
        hAGL = airplaneMSL - airport.alt

        if (distance < 1 and hAGL < 500):
            #isGoAround = True
            print "Airplane is approaching %s, %s" % (airport.city, airport.state)
            temp_list = []
            while hAGL > 150 and hAGL < 500:
                i += 1
                airplaneMSL = parameters[1]['data'][i]
                hAGL = airplaneMSL - airport.alt
            # end while

            start = i

            airplaneLat = parameters[10]['data'][i]
            airplaneLon = parameters[11]['data'][i]
            airplaneHdg = parameters[4]['data'][i]

            runway = detectRunway(airplaneLat, airplaneLon, airplaneHdg, airport)

            while distance < 1 and hAGL <= 150 and hAGL >= 50:
                #isGoAround = False
                airplaneHdg = parameters[4]['data'][i]
                airplaneIAS = parameters[2]['data'][i]
                airplaneVAS = parameters[3]['data'][i]

                if runway is not None:
                    cond_F = 180 - abs(abs(runway.magHeading - airplaneHdg) - 180) <= 5 and abs(crossTrackToCenterLine(airplaneLat, airplaneLon, runway)) <= 50
                else:
                    cond_F = True
                cond_A = airplaneIAS >= 55 and airplaneIAS <= 75
                cond_S = airplaneVAS >= -1000

                if not cond_F or not cond_A or not cond_S:
                    print "F=%s, A=%s, S=%s" % (cond_F, cond_A, cond_S)
                    if not cond_F:
                        print "\tRunway Heading: %s" % runway.magHeading
                        print "\tAirplane Heading: %s" % airplaneHdg
                        print "\tCrossTrackToCenterLine: %s" % crossTrackToCenterLine(airplaneLat, airplaneLon, runway)
                    if not cond_A:
                        print "\tIndicated Airspeed: %s knots" % (airplaneIAS)
                    if not cond_S:
                        print "\tVertical Airspeed: %s ft/min" % (airplaneVAS)
                    temp_list.append(i)

                elif len(temp_list) > 0:
                    exceedances['unstable'].append((temp_list[0], temp_list[-1]))
                    del temp_list[:]
                i += 1

                airplaneMSL = parameters[1]['data'][i]
                airplaneLat = parameters[10]['data'][i]
                airplaneLon = parameters[11]['data'][i]
                distance = haversine(airplaneLat, airplaneLon, airport.lat, airport.lon)
                hAGL = airplaneMSL - airport.alt
            # end while

            end = start if start == i else i - 1

            #if isGoAround: exceedances['go-around'].append((start, end))
            #else:
            if len(temp_list) > 0:
                exceedances['unstable'].append((temp_list[0], temp_list[-1]))
            # end if
            i = analyzeLanding(end, airport)
        # end if

        i += 15
    # end while


'''
This function uses the parameters chosen by the user and graphs
    the time-series data.
It also makes vertical highlights for the regions where exceedances were found.
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

    COLORS = ('cyan', 'orange', 'red', 'lime')
    for key, color in zip(exceedances.keys(), COLORS):
        print key + ": " + str(exceedances[key])
        for x in exceedances[key]: # Vertical Highlight for each exceedance
            axes[0].axvspan( parameters[0]['data'][x[0]], parameters[0]['data'][x[1]], alpha=0.8, color=color )

    plt.title(title % (msg, flightID))

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
    # TODO Check altitude between plane and airport - Wyatt
    # TODO Have function return True/False on whether the plane is going to approach the airport
        (i.e. going in for a landing) - Kelton
'''
def detectAirport(lat, lon):
    closestAirport = -1
    closestDifference = 0
    for key in airports:
        airportLat = airports[key].lat
        airportLon = airports[key].lon
        dLat = abs(lat - airportLat) # getting difference in lat and lon
        dLon = abs(lon - airportLon)
        totalDifference = dLat + dLon # adding the differences so we can compare and see which airport is the closest
        if closestAirport == -1 or totalDifference < closestDifference: # if it is the first time or we found a closer airport
            closestDifference = totalDifference
            closestAirport = key

    return airports[closestAirport]


'''
This function will detect the runway that the airplane is going to attempt to land at.
@param: airplaneLat the latitude of the airplane
@param: airplaneLon the longitude of the airplane
@param: airplaneHdg the heading of the heading
@param: airport the airport object that represents the closest airport to the airplane
@returns: the runway object representing the runway the airplane is attempting to land on
@author: Wyatt Hedrick, Kelton Karboviak
'''
def detectRunway(airplaneLat, airplaneLon, airplaneHdg, airport):
    ourRunway = None
    closestDifference = -1
    for runway in airport.runways:
        if 180 - abs(abs(runway.magHeading - airplaneHdg) - 180) <= 20:
            dLat = abs(runway.centerLat - airplaneLat) # getting difference in lat and lon
            dLon = abs(runway.centerLon - airplaneLon)
            totalDifference = dLat + dLon
            if ourRunway is None or totalDifference < closestDifference:
                ourRunway = runway
                closestDifference = totalDifference

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
def crossTrackToCenterLine(airplaneLat, airplaneLon, runway):
    EARTH_RADIUS_FEET = 20900000  # Radius of the earth in feet
    airplanePoint = LatLon(airplaneLat, airplaneLon)
    runwayCenter = LatLon(runway.centerLat, runway.centerLon)
    hdg = runway.trueHeading

    return airplanePoint.crossTrackDistanceTo(runwayCenter, hdg, EARTH_RADIUS_FEET)


'''
This function calculates the distance (in miles) between 2 coordinates.
Obtained formula from: http://www.movable-type.co.uk/scripts/latlong.html
@param: lat1 the latitude of the first point
@param: lon1 the longitude of the first point
@param: lat2 the latitude of the second point
@param: lon2 the longitude of the second point
@param: radius (Mean) radius of earth (defaults to radius in miles)
@return: the distance between the 2 points, in same units as radius
@author: Wyatt Hedrick, Kelton Karboviak
'''
def haversine(lat1, lon1, lat2, lon2, radius=None):
    radius = 3959 if radius is None else radius

    rLat1 = math.radians(lat1)
    rLat2 = math.radians(lat2)
    deltaLat = math.radians( lat2 - lat1 )
    deltaLon = math.radians( lon2 - lon1 )

    a = math.sin(deltaLat/2) ** 2 +                   \
        math.cos(rLat1) * math.cos(rLat2) *           \
        math.sin(deltaLon/2) ** 2
    c = 2 * math.atan2( math.sqrt(a), math.sqrt(1-a) )
    d = radius * c
    return d # distance between the two points in miles


'''
This function will analyze the time after the final approach and before the plane reaches a height of 150 feet (or until the flight ends if it is the final landing).
@param: start the time index when the approach ends and the landing begins.
@author: Wyatt Hedrick
'''
def analyzeLanding(start, airport):
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
        exceedances['stop-and-go'].append((start, end))
        print "Full Stop!!!!"
    elif touchAndGo:
        exceedances['touch-and-go'].append((start, end))
        print "Touch and Go!!!!"
    else:
        exceedances['go-around'].append((start, end))
        print "Go Around?!?!?!"
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
