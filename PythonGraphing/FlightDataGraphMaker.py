#!/usr/bin/python

import matplotlib.pyplot as plt
import os, sys
import math
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
        'units': 'degrees'}
}

exceedances = {
    'go-around': [],
    'touch-and-go': [],
    'stop-and-go' : [],
    'unstable approach': []
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

    graphsFolder = './graphs/'
    FIRST = True
    for c in choices:
        if FIRST:
            graphsFolder = graphsFolder + parameters[c]['param']
            FIRST = False
        else:
            graphsFolder += 'AND' + parameters[c]['param']

    os.system('mkdir graphs')          # Make graphs folder if it doesn't exist
    os.system('mkdir ' + graphsFolder) # Make folder within graphs for this query

    firstTime = True
    for filename in files:
        if '.csv' not in filename: continue # Skip file if it isn't a .csv
        flight = filename.split('.')[0]
        print 'Generating graph for: {0:}'.format(filename)

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

        analyzeData()

        makeGraph(choices, flight, graphsFolder)
    print 'Complete!!!'


'''
Populate a dictionary containing airport data for all airports throughout the U.S.
@author: Wyatt Hedrick
'''
def getAirportData():
    with open('./Airports.csv', 'r') as file:
        code = ''
        file.readline() # Trash line of data headers
        for line in file:
            row = line.split(',')
            # code, name, city, state, lat, lon, alt
            a = Airport(row[0], row[1], row[2], row[3], float(row[4]), float(row[5]), float(row[6]))
            airports[row[0]] = a # Insert into airports dict with airport_code as key
    
    with open ('./AirportsDetailed.csv', 'r') as file:
        file.readline() # Trash line of data headers
        for line in file:
            row = line.split(',')
            # airport_code, alt, runway_code, heading, centerLat, centerLon
            r = Runway(row[2], float(row[6]), row[10], float(row[11]), float(row[24]), float(row[25]))
            airports[row[2]].addRunway(r) # Add runway to corresponding airport
            print "Added runway " + r.runway_code + " to airport " + row[2]

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
This function analyzes the flight data.
So far we have implemented a check for full stops.
@author: Wyatt Hedrick, Kelton Karboviak
    # TODO Implement go-around detection - Kelton
    # TODO Implement touch-and-go detection - Wyatt
    # TODO Implement unstable vs. stable approach detection - Kelton
    # TODO Report each exceedance that occurred (if any) - Wyatt
'''
def analyzeData():
    findFullStops()

'''
This function finds when the airplane makes a full stop.
It does this by scanning until the indicated airspeed is <= 10 kts.
Then it keeps scanning until it has reached the end of the flight data,
    or the plane has reached 50 kts (which would be a take-off).
Once a full stop has been found, the starting and ending times are added to
    the exceedances list for stop-and-go's as a tuple.
@author: Wyatt Hedrick, Kelton Karboviak
'''
def findFullStops():
    i = 0
    while i < len(parameters[0]['data']):  # Loop through time values
        if parameters[2]['data'][i] <= 25: # Check if 'indicated_airspeed' is less than or equal to 10 kts
            start = i                      # Store starting time index
            while i < len(parameters[0]['data']) and parameters[2]['data'][i] <= 50:
                i += 1                     # Increment while it is less than or equal to 50 kts
            end = i - 1                    # Store ending time index
            exceedances['stop-and-go'].append( (start, end) ) # Append start/end tuple to stop-and-go list
            airport = detectAirport(parameters[10]['data'][start], parameters[11]['data'][start], parameters[1]['data'][start])
            runway = detectRunway(parameters[10]['data'][start], parameters[11]['data'][start], parameters[4]['data'][start], airport)
            if runway != None:
                print str(distanceFromCenterLineNew(parameters[10]['data'][start], parameters[11]['data'][start], runway)) + " feet from center line"
            print ""
        else:
            i += 1

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

    title = 'Time vs {0:} for Flight: {1:}'
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
        ax.set_ylabel( '{0:} ({1:})'.format(parameters[c]['label'], parameters[c]['units']), color=color )
        ax.tick_params(axis='y', colors=color)

    COLORS = ('cyan', 'orange', 'yellow', 'lime')
    for key, color in zip(exceedances.keys(), COLORS):
        for x in exceedances[key]: # Vertical Highlight for each exceedance
            axes[0].axvspan( parameters[0]['data'][x[0]], parameters[0]['data'][x[1]], alpha=0.25, color=color )

    plt.title(title.format(msg, flightID))

    figure = plt.gcf()
    figure.set_size_inches(25.6, 16)
    plt.savefig(folder + '/{0:}.png'.format(flightID), dpi = 100)
    plt.clf()

'''
This function detects the airport that is closest to the passed in coordinates.
It performs this by scanning the airportData dictionary and calculating which
    airport as the lowest total difference between lat/lon.
After it has scanned the dictionary, it then prints out the city, state that it is closest to.
@param: latitude the latitude of the plane
@param: longitude the longitude of the plane
@param: altitude the altitude of the plane
@author: Wyatt Hedrick
    # TODO Check altitude between plane and airport - Wyatt
    # TODO Have function return True/False on whether the plane is going to approach the airport
        (i.e. going in for a landing) - Kelton
'''
def detectAirport(latitude, longitude, altitude):
    closestAirport = -1
    closestDifference = 0
    for key in airports:
        airportLat = airports[key].lat
        airportLong = airports[key].lon
        dLat = abs(latitude - airportLat) # getting difference in latitude and longitude
        dLong = abs(longitude - airportLong)
        totalDifference = dLat + dLong # adding the differences so we can compare and see which airport is the closest
        if closestAirport == -1 or totalDifference < closestDifference: # if it is the first time or we found a closer airport
            closestDifference = totalDifference
            closestAirport = key

    print "Airplane is at: %s, %s" % (airports[closestAirport].city, airports[closestAirport].state)
    return airports[closestAirport]
'''
This function will detect the runway that the airplane is going to attempt to land at.
@param: airplaneLat the latitude of the airplane
@param: airplaneLong the longitude of the airplane
@param: airplaneHeading the heading of the heading
@param: airport the airport object that represents the closest airport to the airplane
@returns: the runway object representing the runway the airplane is attempting to land on
@author: Wyatt Hedrick, Kelton Karboviak
'''
def detectRunway(airplaneLat, airplaneLong, airplaneHeading, airport):
    ourRunway = None
    closestDifference = -1
    for runway in airport.runways:
        dLat = abs(runway.centerLat - airplaneLat) # getting difference in latitude and longitude
        dLong = abs(runway.centerLon - airplaneLong)
        totalDifference = dLat + dLong
        if ourRunway == None or totalDifference < closestDifference:
            ourRunway = runway
            closestDifference = totalDifference
    if ourRunway != None:
        print ourRunway.runway_code
    return ourRunway


'''
This function calculates the distance the airplane is from the center line in feet based on the passed in coordinates of the airplane and the runway the plane is attempting to land at.  

GIS Mapping Tool for verification: http://gistools.igismap.com/bearing

@param: airplaneLat the latitude of the airplane
@param: airplaneLong the longitude of the airplane
@param: runway the runway object representing the closest runway to the airplane
@returns: the distance in feet between the airplane and the center line of the runway
@author: Wyatt Hedrick
'''
def distanceFromCenterLine(airplaneLat, airplaneLong, runway):
    if runway.heading == 0 or runway.heading == 180 or runway.heading == 360:
        return haversine(airplaneLat, airplaneLong, airplaneLat, runway.centerLon)
    else:
        rHdg = math.radians(runway.heading + 90)
        yIntercept = runway.centerLat + math.tan(rHdg) * runway.centerLon
        intersectionPointX = (math.tan(rHdg) * (runway.centerLat + (math.tan(rHdg) * runway.centerLon) - airplaneLat) + airplaneLong)/((math.tan(rHdg) ** 2) + 1)
        intersectionPointY = (-math.tan(rHdg) * intersectionPointX) + yIntercept
        return (haversine(airplaneLat, airplaneLong, intersectionPointY, intersectionPointX) * 5280)

'''
This function calculates the distance (in miles) between 2 coordinates.
Obtained formula from: http://www.movable-type.co.uk/scripts/latlong.html
@param: lat1 the latitude of the first point
@param: lon1 the longitude of the first point
@param: lat2 the latitude of the second point
@param: lon2 the longitude of the second point
@return: the number of miles difference between the 2 points
@author: Wyatt Hedrick, Kelton Karboviak
'''
def haversine(lat1, lon1, lat2, lon2):
    print "Point1: {0} {1} | Point2: {2} {3}".format(lat1, lon1, lat2, lon2)
    lawOfCosines(lat1, lon1, lat2, lon2)
    R = 3959 #in miles
    rLat1 = math.radians(lat1)
    rLat2 = math.radians(lat2)
    deltaLat = math.radians( lat2 - lat1 )
    deltaLon = math.radians( lon2 - lon1 )

    a = math.sin(deltaLat/2) ** 2 +                   \
        math.cos(rLat1) * math.cos(rLat2) *           \
        math.sin(deltaLon/2) ** 2
    c = 2 * math.atan2( math.sqrt(a), math.sqrt(1-a) )
    d = R * c
    return d # distance between the two points in miles

'''
Similarly to the haversine function, this function calculates the distance between two lat/lon points. We are currently keeping both in to find which is more accurate for our case.
@param: lat1 the latitude of the first point
@param: lon1 the longitude of the first point
@param: lat2 the latitude of the second point
@param: lon2 the longitude of the second point
@return: the number of miles difference between the 2 points
@author: Wyatt Hedrick, Kelton Karboviak
'''
def lawOfCosines(lat1, lon1, lat2, lon2):
    R = 3959
    rLat1 = math.radians(lat1)
    rLat2 = math.radians(lat2)
    dLon = math.radians(lon2 - lon1)
    d = math.acos(math.sin(rLat1) * math.sin(rLat2) + math.cos(rLat1) * math.cos(rLat2) * math.cos(dLon)) * R
    print "Law of cosines gives " + str(d * 5280) + " feet"
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
        choice = input('(optional -- enter 0 to opt out) which attribute for y{0:}? '.format(counter+1))
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
