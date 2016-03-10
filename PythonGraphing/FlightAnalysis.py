import math
from LatLon import LatLon
from Vector3d import Vector3d
import os

EARTH_RADIUS_MILES = 3959
EARTH_RADIUS_FEET  = 20900000
APPROACH_MIN_IAS = 55
APPROACH_MAX_IAS = 75
APPROACH_MAX_HEADING_ERROR = 10
APPRAOCH_MIN_VAS = -1000
APPROACH_MAX_CROSSTRACK_ERROR = 50
APPROACH_MIN_DISTANCE = 1
APPROACH_MIN_ALTITUDE_AGL = 500
APPROACH_FINAL_MAX_ALTITUDE_AGL = 150
APPROACH_FINAL_MIN_ALTITUDE_AGL = 50
FULL_STOP_SPEED_INDICATOR = 35
TOUCH_AND_GO_ELEVATION_INDICATOR = 5
RUNWAY_SELECTION_INDICATOR = 20

class FlightAnalyzer:
    parameters = {}
    airports = {}
    approaches = {}
    approachID = 0
    timestamp = ""
    folder = ""
    flightID = ""

    def __init__(self, time, folder, a):
        self.timestamp = time
        self.folder = folder
        self.airports = a

    def analyze(self, flightID, p):
        self.parameters = p
        self.flightID = flightID
        self.clearApproaches()
        start = self.findInitialTakeOff()
        self.analyzeApproaches(start)
        self.outputToCSV()
        self.resetApproachID()
        return self.approaches

    '''
    Function clears the contents of the approaches dictionary
    @author: Kelton Karboviak
    '''
    def clearApproaches(self):
        for key in self.approaches.keys():
            del self.approaches[key]

    '''
    This function will reset the approachID to 0 on the start of a new flight.
    @author Wyatt Hedrick, Kelton Karboviak
    '''
    def resetApproachID(self):
        self.approachID = 0

    '''
    This function will return a unique approachID for each approach in the flight.
    @returns aID the unique approachID associated with the approach.
    @author Wyatt Hedrick, Kelton Karboviak
    '''
    def getApproachID(self):
        aID = self.approachID
        self.approachID += 1
        return aID

    '''
    This function will find the initial takeoff and return the first time value after the initial takeoff
    @return the first time index after the initial takeoff
    '''
    def findInitialTakeOff(self):
        i = 0
        airplaneMSL = self.parameters[1]['data'][i]
        airplanePoint = self.parameters[12]['data'][i]
        airport = self.detectAirport(airplanePoint)
        hAGL = airplaneMSL - airport.alt
        while hAGL < 500 and i < len(self.parameters[0]['data']):
            airplaneMSL = self.parameters[1]['data'][i]
            hAGL = airplaneMSL - airport.alt
            i += 1
        return i


    '''
    This function analyzes the flight data.
    So far we have implemented a check for full stops.
    @param startingIndex the time index after the initial takeoff
    @author: Wyatt Hedrick, Kelton Karboviak
    '''
    def analyzeApproaches(self, startingIndex):
        i = startingIndex
        while i < len(self.parameters[0]['data']):
            airplaneMSL = self.parameters[1]['data'][i]
            airplanePoint = self.parameters[12]['data'][i]

            airport = self.detectAirport(airplanePoint)
            distance = airplanePoint.distanceTo(airport.centerLatLon, EARTH_RADIUS_MILES)
            hAGL = airplaneMSL - airport.alt

            if (distance < APPROACH_MIN_DISTANCE and hAGL < APPROACH_MIN_ALTITUDE_AGL):
                print "Airplane is approaching %s, %s" % (airport.city, airport.state)
                thisApproachID = self.getApproachID()
                self.approaches[thisApproachID] = {}
                self.approaches[thisApproachID]['unstable'] = []
                temp_list = []
                while hAGL > APPROACH_FINAL_MAX_ALTITUDE_AGL and hAGL < APPROACH_MIN_ALTITUDE_AGL:
                    i += 1
                    airplaneMSL = self.parameters[1]['data'][i]
                    hAGL = airplaneMSL - airport.alt
                # end while

                start = i

                airplaneHdg = self.parameters[4]['data'][i]
                airplanePoint = self.parameters[12]['data'][i]

                runway = self.detectRunway(airplanePoint, airplaneHdg, airport)
                unstableReasons = [ [], [], [], [] ]  # F1, F2, A, S
                while distance < APPROACH_MIN_DISTANCE and hAGL <= APPROACH_FINAL_MAX_ALTITUDE_AGL and hAGL >= APPROACH_FINAL_MIN_ALTITUDE_AGL:
                    airplaneHdg = self.parameters[4]['data'][i]
                    airplaneIAS = self.parameters[2]['data'][i]
                    airplaneVAS = self.parameters[3]['data'][i]

                    if runway is not None:
                        cond_F1 = 180 - abs(abs(runway.magHeading - airplaneHdg) - 180) <= APPROACH_MAX_HEADING_ERROR
                        cond_F2 = abs(self.crossTrackToCenterLine(airplanePoint, runway)) <= APPROACH_MAX_CROSSTRACK_ERROR
                    else:
                        cond_F1 = cond_F2 = True
                    cond_A = airplaneIAS >= APPROACH_MIN_IAS and airplaneIAS <= APPROACH_MAX_IAS
                    cond_S = airplaneVAS >= APPRAOCH_MIN_VAS
                    if not cond_F1 or not cond_F2 or not cond_A or not cond_S:
                        print "F1=%s, F2=%s, A=%s, S=%s" % (cond_F1, cond_F2, cond_A, cond_S)
                        if not cond_F1:
                            print "\tRunway Heading: %s" % runway.magHeading
                            print "\tAirplane Heading: %s" % airplaneHdg
                            unstableReasons[0].append(airplaneHdg)
                        if not cond_F2:
                            print "\tCrossTrackToCenterLine: %s" % self.crossTrackToCenterLine(airplanePoint, runway)
                            unstableReasons[1].append( self.crossTrackToCenterLine(airplanePoint, runway) )
                        if not cond_A:
                            print "\tIndicated Airspeed: %s knots" % (airplaneIAS)
                            unstableReasons[2].append(airplaneIAS)
                        if not cond_S:
                            print "\tVertical Airspeed: %s ft/min" % (airplaneVAS)
                            unstableReasons[3].append(airplaneVAS)
                        temp_list.append(i)
                    elif len(temp_list) > 0:
                        self.approaches[thisApproachID]['unstable'].append( (temp_list[0], temp_list[-1]) )
                        del temp_list[:]
                    i += 1

                    airplaneMSL = self.parameters[1]['data'][i]
                    airplanePoint = self.parameters[12]['data'][i]
                    distance = airplanePoint.distanceTo(airport.centerLatLon, EARTH_RADIUS_MILES)
                    hAGL = airplaneMSL - airport.alt
                # end while

                end = start if start == i else i - 1

                if len(temp_list) > 0:
                    self.approaches[thisApproachID]['unstable'].append( (temp_list[0], temp_list[-1]) )
                # end if

                self.approaches[thisApproachID]['runway-code'] = runway.runwayCode
                self.approaches[thisApproachID]['F1'] = unstableReasons[0]
                self.approaches[thisApproachID]['F2'] = unstableReasons[1]
                self.approaches[thisApproachID]['A']  = unstableReasons[2]
                self.approaches[thisApproachID]['S']  = unstableReasons[3]

                i = self.analyzeLanding(end, airport, thisApproachID)
            # end if

            i += 15
        # end while

    '''
    This function will analyze the time after the final approach and before the plane reaches a height of 150 feet (or until the flight ends if it is the final landing).
    @param: start the time index when the approach ends and the landing begins.
    @param: airport the airport that the airplane is attempting to land at
    @author: Wyatt Hedrick
    '''
    def analyzeLanding(self, start, airport, thisApproachID):
        i = start
        airplaneMSL = self.parameters[1]['data'][i]
        hAGL = airplaneMSL - airport.alt
        fullStop = False
        elevations = []
        deltaElevation = TOUCH_AND_GO_ELEVATION_INDICATOR + 1

        fullStop = touchAndGo = False

        while hAGL < APPROACH_MIN_ALTITUDE_AGL and i < len(self.parameters[0]['data']) - 1:
            airplaneIAS = self.parameters[2]['data'][i]
            if (not fullStop):
                if airplaneIAS <= FULL_STOP_SPEED_INDICATOR:
                    fullStop = True
                elif deltaElevation <= TOUCH_AND_GO_ELEVATION_INDICATOR:
                    touchAndGo = True
            i += 1
            airplaneMSL = self.parameters[1]['data'][i]
            hAGL = airplaneMSL - airport.alt
            if len(elevations) < 5:
                elevations.append(hAGL)
            else:
                elevations.pop(0)
                elevations.append(hAGL)
                deltaElevation = sum(elevations)/len(elevations)
        end = i

        if fullStop:
            self.approaches[thisApproachID]['landing-type'] = 'stop-and-go'
            print "Full Stop!!!!"
        elif touchAndGo:
            self.approaches[thisApproachID]['landing-type'] = 'touch-and-go'
            print "Touch and Go!!!!"
        else:
            self.approaches[thisApproachID]['landing-type'] = 'go-around'
            print "Go Around?!?!?!"

        self.approaches[thisApproachID]['airport-code'] = airport.code
        self.approaches[thisApproachID]['landing-start'] = start
        self.approaches[thisApproachID]['landing-end'] = end
        print ""
        return end


    '''
    This function calculates the distance the airplane is from the center line in feet based on the passed in coordinates of the airplane and the runway the plane is attempting to land at.

    GIS Mapping Tool for verification: http://gistools.igismap.com/bearing

    @param: airplaneLat the latitude of the airplane
    @param: airplaneLon the longitude of the airplane
    @param: runway the runway object representing the closest runway to the airplane
    @returns: the distance in feet between the airplane and the center line of the runway
    @author: Wyatt Hedrick, Kelton Karboviak
    '''
    def crossTrackToCenterLine(self, airplanePoint, runway):
        return airplanePoint.crossTrackDistanceTo(runway.centerLatLon, runway.trueHeading, EARTH_RADIUS_FEET)


    '''
    This function detects the airport that is closest to the passed in coordinates.
    It performs this by scanning the airportData dictionary and calculating which
        airport as the lowest total difference between lat/lon.
    @param: lat the latitude of the plane
    @param: lon the longitude of the plane
    @author: Wyatt Hedrick
    '''
    def detectAirport(self, airplanePoint):
        ourAirport = None
        closestDifference = 0
        for key, airport in self.airports.items():
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
    def detectRunway(self, airplanePoint, airplaneHdg, airport):
        ourRunway = None
        closestDifference = 0
        for runway in airport.runways:
            if 180 - abs(abs(runway.magHeading - airplaneHdg) - 180) <= RUNWAY_SELECTION_INDICATOR:
                dLat = abs(runway.centerLatLon.lat - airplanePoint.lat) # getting difference in lat and lon
                dLon = abs(runway.centerLatLon.lon - airplanePoint.lon)
                totalDifference = dLat + dLon
                if ourRunway is None or totalDifference < closestDifference:
                    ourRunway = runway
                    closestDifference = totalDifference
        # end for
        return ourRunway

    '''
    Outputs the approach analysis information to a .csv file. The file will be saved to
        ./results/results_flightID.csv, and appended to ./results/query_timestamp.csv
    @param flightID string of the current flight ID to write to a CSV file
    @param timestamp string of the timestamp when the program started running.
        This will be used as the filename to store the results of all flights for this program run
    @param folder string of the folder in which to store the result CSV file
    @author: Kelton Karboviak
    '''
    def outputToCSV(self):
        with open('%s/query_%s.csv' % (self.folder, self.timestamp), 'a') as globalOutput:
            with open('%s/results_%s.csv' % (self.folder, self.flightID), 'w') as output:
                header = 'Flight_ID,Approach_ID,Airport_ID,Runway_ID,Landing_Start,Landing_End,Landing_Type,Unstable?,F1_Heading,F2_CT,A_IAS,S_VAS\n'
                if os.stat(globalOutput.name).st_size == 0:
                    globalOutput.write(header)
                output.write(header)
                for ID, approach in self.approaches.items():
                    lineToWrite = '%s,%d,%s,%s,%d,%d,%s,%s,%s,%s,%s,%s\n' % \
                                  (self.flightID,
                                   ID,
                                   approach['airport-code'],
                                   approach['runway-code'],
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
