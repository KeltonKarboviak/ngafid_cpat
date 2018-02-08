import MySQLdb as mysql


''' GLOBAL EXCEEDANCE THRESHOLDS '''
EARTH_RADIUS_MILES = 3959
EARTH_RADIUS_FEET = 20900000
APPROACH_MIN_IAS = 55
APPROACH_MAX_IAS = 75
APPROACH_MAX_HEADING_ERROR = 10
APPROACH_MIN_VSI = -1000
APPROACH_MAX_CROSSTRACK_ERROR = 50
APPROACH_MIN_DISTANCE = 1
APPROACH_MIN_ALTITUDE_AGL = 500
APPROACH_FINAL_MAX_ALTITUDE_AGL = 150
APPROACH_FINAL_MIN_ALTITUDE_AGL = 50
FULL_STOP_SPEED_INDICATOR = 35
TOUCH_AND_GO_ELEVATION_INDICATOR = 5
RUNWAY_SELECTION_INDICATOR = 20

selectThresholdsSQL = "SELECT * FROM exceedance_thresholds WHERE aircraft_id = %s;"

insertKeysList = [
    "flight_id", "approach_id", "airport_id", "runway_id",
    "approach_start", "approach_end", "landing_start", "landing_end", "landing_type",
    "unstable", "all_heading", "f1_heading", "all_crosstrack", "f2_crosstrack", "all_ias", "a_ias", "all_vsi", "s_vsi"
]
insertKeysSQL = ', '.join(insertKeysList)
insertUpdateValuesSQL = ', '.join(["{0}=VALUES({0})".format(key) for key in insertKeysList])
insertValuesPlaceholders = ', '.join(["%s"] * len(insertKeysList))
insertSQL = "INSERT INTO approaches (%s) VALUES (%s) ON DUPLICATE KEY UPDATE %s;" % (insertKeysSQL, insertValuesPlaceholders, insertUpdateValuesSQL)

updateAnalysesSQL = "UPDATE flight_analyses SET approach_analysis = 1 WHERE flight_id = %s"


class FlightAnalyzer(object):

    def __init__(self, db, cursor, airports, skipOutput=False):
        self.db = db
        self.cursor = cursor
        self.airports = airports
        self.skipOutputToDB = skipOutput
        self.approaches = {}
        self.approachID = 0

    def analyze(self, flightID, aircraftType, data, skipAnalysis=False):
        self.flightID = flightID
        self.flightData = data
        self.dataLength = len(data)

        if not skipAnalysis and self.dataLength > 0:
            self.setThresholds(aircraftType)
            start = self.findInitialTakeOff()
            self.analyzeApproaches(start)

        if not self.skipOutputToDB:
            self.outputToDB()

        # Reset global variables for next analysis
        self.clearApproaches()
        self.resetApproachID()

        # Return the dict of approaches
        return self.approaches

    def setThresholds(self, aircraftType):
        self.cursor.execute(selectThresholdsSQL, (aircraftType,))
        row = self.cursor.fetchone()

        APPROACH_MIN_IAS = row['approach_min_ias']
        APPROACH_MAX_IAS = row['approach_max_ias']
        APPROACH_MAX_HEADING_ERROR = row['approach_max_heading_error']
        APPROACH_MIN_VSI = row['approach_min_vas']
        APPROACH_MAX_CROSSTRACK_ERROR = row['approach_max_crosstrack_error']
        APPROACH_MIN_DISTANCE = row['approach_min_distance']
        APPROACH_MIN_ALTITUDE_AGL = row['approach_min_altitude_agl']
        APPROACH_FINAL_MAX_ALTITUDE_AGL = row['approach_final_max_altitude_agl']
        APPROACH_FINAL_MIN_ALTITUDE_AGL = row['approach_final_min_altitude_agl']
        FULL_STOP_SPEED_INDICATOR = row['full_stop_speed_indicator']
        TOUCH_AND_GO_ELEVATION_INDICATOR = row['touch_and_go_elevation_indicator']
        RUNWAY_SELECTION_INDICATOR = row['runway_selection_indicator']

    def clearApproaches(self):
        '''
        Function clears the contents of the approaches dictionary
        @author: Kelton Karboviak
        '''
        self.approaches.clear()

    def resetApproachID(self):
        '''
        This function will reset the approachID to 0 on the start of a new flight.
        @author Wyatt Hedrick, Kelton Karboviak
        '''
        self.approachID = 0

    def getAndIncApproachID(self):
        '''
        This function will return a unique approachID for each approach in the flight.
        @return aID the unique approachID associated with the approach.
        @author Wyatt Hedrick, Kelton Karboviak
        '''
        aID = self.approachID
        self.approachID += 1
        return aID

    def findInitialTakeOff(self):
        '''
        This function will find the initial takeoff and return the first time value after the initial takeoff
        @return the first time index after the initial takeoff
        '''
        i = 0
        airplaneMSL = self.flightData[i]['msl_altitude']
        airplanePoint = self.flightData[i]['LatLon']
        airport = self.detectAirport(airplanePoint)
        hAGL = airplaneMSL - airport.alt
        while hAGL < 500 and i < self.dataLength:
            airplaneMSL = self.flightData[i]['msl_altitude']
            hAGL = airplaneMSL - airport.alt
            i += 1
        return i

    def headingDifference(self, hdg1, hdg2):
        return 180 - abs(abs(hdg1 - hdg2) - 180)

    def analyzeApproaches(self, startingIndex):
        '''
        This function analyzes the flight data.
        So far we have implemented a check for full stops.
        @param startingIndex the time index after the initial takeoff
        @author: Wyatt Hedrick, Kelton Karboviak
        '''
        i = startingIndex
        while i < self.dataLength:
            airplaneMSL = self.flightData[i]['msl_altitude']
            airplanePoint = self.flightData[i]['LatLon']

            airport = self.detectAirport(airplanePoint)
            distance = airplanePoint.distanceTo(airport.centerLatLon, EARTH_RADIUS_MILES)
            hAGL = airplaneMSL - airport.alt

            if distance < APPROACH_MIN_DISTANCE and hAGL < APPROACH_MIN_ALTITUDE_AGL:
                print("Airplane is approaching %s, %s: %s" % (airport.city, airport.state, airport.code))

                # hdgDiff = self.headingDifference(airport.magHeading, self.flightData[i]['heading'])
                # if hdgDiff > 90:
                #     print "\tcompCourse greater than 90: %f, time: %f" % (hdgDiff, self.flightData[i]['time'])
                # elif hdgDiff > 15 and hdgDiff < 90:
                #     print "\tcompCourse 15 < x < 90: %f, time: %f" % (hdgDiff, self.flightData[i]['time'])

                thisApproachID = self.getAndIncApproachID()
                self.approaches[thisApproachID] = {}
                self.approaches[thisApproachID]['unstable'] = []

                while hAGL > APPROACH_FINAL_MAX_ALTITUDE_AGL and hAGL < APPROACH_MIN_ALTITUDE_AGL and i < self.dataLength:
                    airplaneMSL = self.flightData[i]['msl_altitude']
                    hAGL = airplaneMSL - airport.alt
                    i += 1

                # Decrement by 1 so that we are guaranteed that i < dataLength
                start = i - 1

                airplaneHdg = self.flightData[start]['heading']
                airplanePoint = self.flightData[start]['LatLon']

                runway = self.detectRunway(airplanePoint, airplaneHdg, airport)

                print("Runway:", "Unknown" if runway is None else runway.runwayCode)

                temp_list = []
                allValues = [ [], [], [], [] ]
                unstableReasons = [ [], [], [], [] ]  # F1, F2, A, S
                while distance < APPROACH_MIN_DISTANCE and hAGL <= APPROACH_FINAL_MAX_ALTITUDE_AGL and hAGL >= APPROACH_FINAL_MIN_ALTITUDE_AGL and i < self.dataLength:
                    airplaneHdg = self.flightData[i]['heading']
                    airplaneIAS = self.flightData[i]['indicated_airspeed']
                    airplaneVSI = self.flightData[i]['vertical_airspeed']

                    if runway is not None:
                        headingError = 180 - abs(abs(runway.magHeading - airplaneHdg) - 180)
                        cond_F1 = headingError <= APPROACH_MAX_HEADING_ERROR
                        crossTrackError = self.crossTrackToCenterLine(airplanePoint, runway)
                        cond_F2 = abs(crossTrackError) <= APPROACH_MAX_CROSSTRACK_ERROR
                    else:
                        cond_F1 = cond_F2 = True

                    cond_A = airplaneIAS >= APPROACH_MIN_IAS and airplaneIAS <= APPROACH_MAX_IAS
                    cond_S = airplaneVSI >= APPROACH_MIN_VSI

                    # Check to see if any parameters went unstable.
                    # if a condition is false, that means it was unstable
                    airplaneIsUnstable = not (cond_F1 and cond_F2 and cond_A and cond_S)

                    if airplaneIsUnstable:
                        print("F1=%s, F2=%s, A=%s, S=%s" % (cond_F1, cond_F2, cond_A, cond_S))
                        if not cond_F1:
                            print("\tRunway Heading: %s" % runway.magHeading)
                            print("\tAirplane Heading: %s" % airplaneHdg)
                            unstableReasons[0].append(headingError)
                        if not cond_F2:
                            print("\tCrossTrackToCenterLine: %s" % crossTrackError)
                            unstableReasons[1].append(crossTrackError)
                        if not cond_A:
                            print("\tIndicated Airspeed: %s knots" % (airplaneIAS))
                            unstableReasons[2].append(airplaneIAS)
                        if not cond_S:
                            print("\tVertical Airspeed: %s ft/min" % (airplaneVSI))
                            unstableReasons[3].append(airplaneVSI)
                        temp_list.append(i)
                    elif len(temp_list) > 0:
                        self.approaches[thisApproachID]['unstable'].append( (temp_list[0], temp_list[-1]) )
                        del temp_list[:]

                    # Including the parameter values whether the approach is
                    # stable or unstable for being able to do comparisons with
                    # the parameter distributions
                    if runway is not None:
                        allValues[0].append(headingError)
                        allValues[1].append(crossTrackError)
                    allValues[2].append(airplaneIAS)
                    allValues[3].append(airplaneVSI)

                    airplaneMSL = self.flightData[i]['msl_altitude']
                    airplanePoint = self.flightData[i]['LatLon']
                    distance = airplanePoint.distanceTo(airport.centerLatLon, EARTH_RADIUS_MILES)
                    hAGL = airplaneMSL - airport.alt

                    i += 1

                end = start if start == i - 1 else i - 1

                if len(temp_list) > 0:
                    self.approaches[thisApproachID]['unstable'].append( (temp_list[0], temp_list[-1]) )

                self.approaches[thisApproachID]['airport-code'] = airport.code
                self.approaches[thisApproachID]['runway-code'] = None if runway is None else runway.runwayCode
                self.approaches[thisApproachID]['approach-start'] = start
                self.approaches[thisApproachID]['approach-end'] = end
                self.approaches[thisApproachID]['F1'] = unstableReasons[0]
                self.approaches[thisApproachID]['F2'] = unstableReasons[1]
                self.approaches[thisApproachID]['A'] = unstableReasons[2]
                self.approaches[thisApproachID]['S'] = unstableReasons[3]
                self.approaches[thisApproachID]['HDG'] = allValues[0]
                self.approaches[thisApproachID]['CTR'] = allValues[1]
                self.approaches[thisApproachID]['IAS'] = allValues[2]
                self.approaches[thisApproachID]['VSI'] = allValues[3]

                i = self.analyzeLanding(end, airport, thisApproachID)

            i += 15

    def analyzeLanding(self, start, airport, thisApproachID):
        '''
        This function will analyze the time after the final approach and before the plane reaches a height of 150 feet (or until the flight ends if it is the final landing).
        @param: start the time index when the approach ends and the landing begins.
        @param: airport the airport that the airplane is attempting to land at
        @author: Wyatt Hedrick
        '''
        i = start
        airplaneMSL = self.flightData[i]['msl_altitude']
        hAGL = airplaneMSL - airport.alt
        elevations = []
        avgElevation = TOUCH_AND_GO_ELEVATION_INDICATOR + 1

        fullStop = touchAndGo = False

        while hAGL < APPROACH_MIN_ALTITUDE_AGL and i < self.dataLength - 1:
            if not fullStop:
                airplaneIAS = self.flightData[i]['indicated_airspeed']
                if airplaneIAS <= FULL_STOP_SPEED_INDICATOR:
                    fullStop = True
                elif avgElevation <= TOUCH_AND_GO_ELEVATION_INDICATOR:
                    touchAndGo = True

            i += 1
            airplaneMSL = self.flightData[i]['msl_altitude']
            hAGL = airplaneMSL - airport.alt

            if len(elevations) < 5:
                elevations.append(hAGL)
            else:
                elevations.pop(0)
                elevations.append(hAGL)
                avgElevation = sum(elevations) / len(elevations)

        end = i

        if fullStop:
            self.approaches[thisApproachID]['landing-type'] = 'stop-and-go'
            print("Full Stop!!!!")
        elif touchAndGo:
            self.approaches[thisApproachID]['landing-type'] = 'touch-and-go'
            print("Touch and Go!!!!")
        else:
            self.approaches[thisApproachID]['landing-type'] = 'go-around'
            print("Go Around?!?!?!")

        self.approaches[thisApproachID]['landing-start'] = start
        self.approaches[thisApproachID]['landing-end'] = end
        print("")

        return end

    def crossTrackToCenterLine(self, airplanePoint, runway):
        '''
        This function calculates the distance the airplane is from the center line in feet based on the passed in coordinates of the airplane and the runway the plane is attempting to land at.

        GIS Mapping Tool for verification: http://gistools.igismap.com/bearing

        @param: airplaneLat the latitude of the airplane
        @param: airplaneLon the longitude of the airplane
        @param: runway the runway object representing the closest runway to the airplane
        @return: the distance in feet between the airplane and the center line of the runway
        @author: Wyatt Hedrick, Kelton Karboviak
        '''
        return airplanePoint.crossTrackDistanceTo(runway.centerLatLon, runway.trueHeading, EARTH_RADIUS_FEET)

    def detectAirport(self, airplanePoint):
        '''
        This function detects the airport that is closest to the passed in coordinates.
        It performs this by scanning the airportData dictionary and calculating which
            airport as the lowest total difference between lat/lon.
        @param: lat the latitude of the plane
        @param: lon the longitude of the plane
        @author: Wyatt Hedrick
        '''
        ourAirport = None
        closestDifference = 0
        for key, airport in self.airports.items():
            dLat = abs(airport.centerLatLon.lat - airplanePoint.lat)  # getting difference in lat and lon
            dLon = abs(airport.centerLatLon.lon - airplanePoint.lon)
            totalDifference = dLat + dLon  # adding the differences so we can compare and see which airport is the closest
            if ourAirport is None or totalDifference < closestDifference:  # if it is the first time or we found a closer airport
                ourAirport = airport
                closestDifference = totalDifference

        return ourAirport

    def detectRunway(self, airplanePoint, airplaneHdg, airport):
        '''
        This function will detect the runway that the airplane is going to attempt to land at.
        @param: airplaneLat the latitude of the airplane
        @param: airplaneLon the longitude of the airplane
        @param: airplaneHdg the heading of the heading
        @param: airport the airport object that represents the closest airport to the airplane
        @return: the runway object representing the runway the airplane is attempting to land on
        @author: Wyatt Hedrick, Kelton Karboviak
        '''
        ourRunway = None
        closestDifference = 0
        for runway in airport.runways:
            if 180 - abs(abs(runway.magHeading - airplaneHdg) - 180) <= RUNWAY_SELECTION_INDICATOR:
                dLat = abs(runway.centerLatLon.lat - airplanePoint.lat)  # getting difference in lat and lon
                dLon = abs(runway.centerLatLon.lon - airplanePoint.lon)
                totalDifference = dLat + dLon
                if ourRunway is None or totalDifference < closestDifference:
                    ourRunway = runway
                    closestDifference = totalDifference

        return ourRunway

    def outputToDB(self):
        '''
        Outputs the approach analysis information to the approaches table
            within the database.
        @return: None
        @author: Kelton Karboviak
        '''
        values = []
        for id, approach in self.approaches.items():
            valuesTup = (
                self.flightID,
                id + 1,
                approach['airport-code'],
                approach['runway-code'],
                approach['approach-start'],
                approach['approach-end'],
                approach['landing-start'],
                approach['landing-end'],
                approach['landing-type'],
                int( len(approach['unstable']) > 0 ),
                None if len(approach['HDG']) == 0 else sum(approach['HDG']) / len(approach['HDG']),
                None if len(approach['F1']) == 0 else sum(approach['F1']) / len(approach['F1']),
                None if len(approach['CTR']) == 0 else sum(approach['CTR']) / len(approach['CTR']),
                None if len(approach['F2']) == 0 else sum(approach['F2']) / len(approach['F2']),
                None if len(approach['IAS']) == 0 else sum(approach['IAS']) / len(approach['IAS']),
                None if len(approach['A']) == 0 else sum(approach['A']) / len(approach['A']),
                None if len(approach['VSI']) == 0 else sum(approach['VSI']) / len(approach['VSI']),
                None if len(approach['S']) == 0 else sum(approach['S']) / len(approach['S']),
            )
            values.append(valuesTup)

        print('\n'.join(str(tup) for tup in values))

        try:
            if len(values):  # Check to see if flight has any approaches to insert
                self.cursor.executemany(insertSQL, values)
            self.cursor.execute( updateAnalysesSQL, (self.flightID,) )
            self.db.commit()
        except mysql.Error as e:
            print("MySQL Error [%d]: %s\n" % (e.args[0], e.args[1]))
            print("Last Executed Query: ", self.cursor._last_executed)
            self.db.rollback()
