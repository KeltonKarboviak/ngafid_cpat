# -*- coding: utf-8 -*-

import MySQLdb as mysql
import pandas as pd
import numpy as np
from numpy import absolute
from enum import Enum
from geoutils import (
    signed_heading_difference,
    unsigned_heading_difference,
    vincenty_distance,
    cross_track_distance_from_point_to_path,
)
from quad_tree import QuadTree


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

SELECT_THRESHOLDS_SQL = "SELECT * FROM exceedance_thresholds WHERE aircraft_id = %s;"

INSERT_KEYS_LIST = [
    "flight_id", "approach_id", "airport_id", "runway_id",
    "approach_start", "approach_end", "landing_start", "landing_end", "landing_type",
    "unstable", "all_heading", "f1_heading", "all_crosstrack", "f2_crosstrack", "all_ias", "a_ias", "all_vsi", "s_vsi"
]
INSERT_KEYS_SQL = ', '.join(INSERT_KEYS_LIST)
INSERT_UPDATE_VALUES_SQL = ', '.join(["{0}=VALUES({0})".format(key) for key in INSERT_KEYS_LIST])
INSERT_VALUES_PLACEHOLDERS = ', '.join(["%s"] * len(INSERT_KEYS_LIST))
INSERT_SQL = "INSERT INTO approaches (%s) VALUES (%s) ON DUPLICATE KEY UPDATE %s;" % (INSERT_KEYS_SQL, INSERT_VALUES_PLACEHOLDERS, INSERT_UPDATE_VALUES_SQL)

UPDATE_ANALYSES_SQL = "UPDATE flight_analyses SET approach_analysis = 1 WHERE flight_id = %s;"


LandingResult = Enum('LandingResult', {
    'STOP_AND_GO': 'stop-and-go',
    'TOUCH_AND_GO': 'touch-and-go',
    'GO_AROUND': 'go-around',
})


def rolling_window(a, window):
    shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
    strides = a.strides + (a.strides[-1],)
    return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)


class FlightAnalyzer(object):

    def __init__(self, db: mysql.Connection, quad_tree: QuadTree, skip_output: bool = False):
        self._db = db
        self._cursor = db.cursor(mysql.cursors.DictCursor)
        self._quad_tree = quad_tree
        self._skip_output_to_db = skip_output
        self._approaches = {}
        self._approach_id = 0

        self.vector_get_nearest_airports = np.vectorize(self._quad_tree.get_nearest_airport)
        self.vector_cross_track_distance = np.vectorize(self._crossTrackToCenterLine)

    def analyze(self, flight_id: int, aircraft_type_id: int, data: pd.DataFrame, skip_analysis: bool = False) -> dict:
        self._flight_id = flight_id

        self._flight_data = self._derive_necessary_data(data)
        self._data_length = len(data.index)

        if not skip_analysis and self._data_length > 0:
            # self._setThresholds(aircraft_type_id)
            start = self._findInitialTakeOff()
            self._analyze_approaches(start)

        # if not self.skipOutputToDB:
        self._outputToDB()

        # Reset global variables for next analysis
        self._clearApproaches()
        self._resetApproachID()

        # Return the dict of approaches
        return self._approaches

    def _derive_necessary_data(self, df: pd.DataFrame) -> pd.DataFrame:
        # Get airport that is closest to each point
        df.loc[:, 'airport'] = self.vector_get_nearest_airports(
            *df[['latitude', 'longitude']].T.values
        )

        # Get distance from airplane to closest airport at each point
        airports = df['airport'].values
        airplane_data = df[['latitude', 'longitude']].T.values
        airport_data = (
            [a.centerLatLon.lat for a in airports],
            [a.centerLatLon.lon for a in airports],
        )
        df.loc[:, 'distance'] = vincenty_distance(*airplane_data, *airport_data) * 5280

        # Get AGL at each point
        if 'radio_altitude_derived' not in df.columns:
            df.loc[:, 'radio_altitude_derived'] = airplane_data[2] - airport_data[2]

        return df

    def _setThresholds(self, aircraft_type_id: int):
        self._cursor.execute(SELECT_THRESHOLDS_SQL, (aircraft_type_id,))
        row = self._cursor.fetchone()

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

    def _clearApproaches(self):
        '''
        Function clears the contents of the approaches dictionary
        @author: Kelton Karboviak
        '''
        self._approaches.clear()

    def _resetApproachID(self):
        '''
        This function will reset the approachID to 0 on the start of a new flight.
        @author Wyatt Hedrick, Kelton Karboviak
        '''
        self._approach_id = 0

    def _getAndIncApproachID(self):
        '''
        This function will return a unique approachID for each approach in the flight.
        @return aID the unique approachID associated with the approach.
        @author Wyatt Hedrick, Kelton Karboviak
        '''
        aID = self._approach_id
        self._approach_id += 1
        return aID

    def _findInitialTakeOff(self) -> int:
        # This will return the first index where the condition is True
        return (
            self._flight_data['radio_altitude_derived'] >= APPROACH_MIN_ALTITUDE_AGL
        ).idxmax()

    def _analyze_approaches(self, idx_takeoff_end: int):
        try:
            # We'll loop until we go out of bounds on self._flight_data (see the
            # except block).
            while idx_takeoff_end < len(self._flight_data.index) - 1:
                mask_within_mile_below_500_ft = (
                    (self._flight_data.loc[idx_takeoff_end:, 'distance'] < 5280) &
                    (self._flight_data.loc[idx_takeoff_end:, 'radio_altitude_derived'] < APPROACH_MIN_ALTITUDE_AGL)
                )
                idx_approach_attempt = mask_within_mile_below_500_ft.idxmax()

                airport = self._flight_data.loc[idx_approach_attempt, 'airport']

                print("Airplane is approaching %s, %s: %s" % (airport.city, airport.state, airport.code))
                thisApproachID = self._getAndIncApproachID()
                self._approaches[thisApproachID] = {}

                mask_not_between_150_500_ft_agl = ~self._flight_data.loc[
                    idx_approach_attempt:, 'radio_altitude_derived'
                ].between(
                    APPROACH_FINAL_MAX_ALTITUDE_AGL,
                    APPROACH_MIN_ALTITUDE_AGL,
                    inclusive=False
                )
                idx_start = mask_not_between_150_500_ft_agl.idxmax()

                runway = self._detectRunway(
                    *self._flight_data.loc[idx_start, ['LatLon', 'heading']].values,
                    airport
                )

                mask_not_within_mile_between_50_150_ft = ~(
                    (self._flight_data.loc[idx_start:, 'distance'] < 5280) &
                    (self._flight_data.loc[idx_start:, 'radio_altitude_derived'].between(
                        APPROACH_FINAL_MIN_ALTITUDE_AGL,
                        APPROACH_FINAL_MAX_ALTITUDE_AGL,
                        inclusive=True
                    ))
                )
                idx_end = mask_not_within_mile_between_50_150_ft.idxmax()

                approach_data_slice = self._flight_data.iloc[idx_start : idx_end+1]

                self._analyze_single_approach(
                    approach_data_slice, airport, runway, thisApproachID
                )

                # Perform parameter analyses
                all_values = [[], [], [], []]
                unstable_reasons = [[], [], [], []]
                airplane_is_unstable = False

                if len(approach_data_slice.index):
                    # If the slice of data isn't empty
                    if runway is not None:
                        heading_errors = signed_heading_difference(
                            runway.magHeading, approach_data_slice['heading'].values
                        )
                        cond_F1 = absolute(heading_errors) <= APPROACH_MAX_HEADING_ERROR

                        cross_track_errors = self.vector_cross_track_distance(
                            approach_data_slice['LatLon'], runway
                        )
                        cond_F2 = absolute(cross_track_errors) <= APPROACH_MAX_CROSSTRACK_ERROR
                    else:
                        cond_F1 = cond_F2 = np.full_like(approach_data_slice.index, True)

                    cond_A = approach_data_slice['indicated_airspeed'].between(
                        APPROACH_MIN_IAS, APPROACH_MAX_IAS, inclusive=True
                    ).values
                    cond_S = approach_data_slice['vertical_airspeed'].values >= APPROACH_MIN_VSI

                    # Check to see if any parameters went unstable.
                    # if a condition is false, that means it was unstable
                    airplane_is_unstable = not (
                        cond_F1 & cond_F2 & cond_A & cond_S
                    ).all()

                    # Get unstable parameter values
                    # For each param, check if there was at least 1 unstable parameter
                    # instance. If so, then we'll grab only the values from the slice
                    # that failed the condition
                    if not cond_F1.all():
                        unstable_reasons[0] = heading_errors[~cond_F1]
                    if not cond_F2.all():
                        unstable_reasons[1] = cross_track_errors[~cond_F2]
                    if not cond_A.all():
                        unstable_reasons[2] = (
                            approach_data_slice['indicated_airspeed'].values[~cond_A]
                        )
                    if not cond_S.all():
                        unstable_reasons[3] = (
                            approach_data_slice['vertical_airspeed'].values[~cond_S]
                        )

                    # Get all parameter values in the approach (stable or unstable)
                    if runway is not None:
                        all_values[0] = heading_errors
                        all_values[1] = cross_track_errors
                    all_values[2] = approach_data_slice['indicated_airspeed'].values
                    all_values[3] = approach_data_slice['vertical_airspeed'].values

                self._approaches[thisApproachID]['airport-code'] = airport.code
                self._approaches[thisApproachID]['runway-code'] = None if runway is None else runway.runwayCode
                self._approaches[thisApproachID]['approach-start'] = idx_start
                self._approaches[thisApproachID]['approach-end'] = idx_end
                self._approaches[thisApproachID]['unstable'] = airplane_is_unstable
                self._approaches[thisApproachID]['F1'] = unstable_reasons[0]
                self._approaches[thisApproachID]['F2'] = unstable_reasons[1]
                self._approaches[thisApproachID]['A'] = unstable_reasons[2]
                self._approaches[thisApproachID]['S'] = unstable_reasons[3]
                self._approaches[thisApproachID]['HDG'] = all_values[0]
                self._approaches[thisApproachID]['CTR'] = all_values[1]
                self._approaches[thisApproachID]['IAS'] = all_values[2]
                self._approaches[thisApproachID]['VSI'] = all_values[3]

                idx_takeoff_end = self._analyze_landing(idx_end, airport, thisApproachID)
        except (KeyError, IndexError) as e:
            # We went out of bounds on an index in self._flight_data, which means
            # we've gone through all the data. Thus, return out of function
            print('Hit the except block!!!')
            return


    # def _analyzeApproaches(self, startingIndex):
    #     '''
    #     This function analyzes the flight data.
    #     So far we have implemented a check for full stops.
    #     @param startingIndex the time index after the initial takeoff
    #     @author: Wyatt Hedrick, Kelton Karboviak
    #     '''
    #     i = startingIndex
    #     while i < self.dataLength:
    #         airplaneMSL = self.flightData[i]['msl_altitude']
    #         airplanePoint = self.flightData[i]['LatLon']

    #         airport = self.detectAirport(airplanePoint)
    #         distance = airplanePoint.distanceTo(airport.centerLatLon, EARTH_RADIUS_MILES)
    #         hAGL = airplaneMSL - airport.alt

    #         if distance < APPROACH_MIN_DISTANCE and hAGL < APPROACH_MIN_ALTITUDE_AGL:
    #             print("Airplane is approaching %s, %s: %s" % (airport.city, airport.state, airport.code))

    #             # hdgDiff = self.headingDifference(airport.magHeading, self.flightData[i]['heading'])
    #             # if hdgDiff > 90:
    #             #     print "\tcompCourse greater than 90: %f, time: %f" % (hdgDiff, self.flightData[i]['time'])
    #             # elif hdgDiff > 15 and hdgDiff < 90:
    #             #     print "\tcompCourse 15 < x < 90: %f, time: %f" % (hdgDiff, self.flightData[i]['time'])

    #             thisApproachID = self._getAndIncApproachID()
    #             self._approaches[thisApproachID] = {}
    #             self._approaches[thisApproachID]['unstable'] = []

    #             while hAGL > APPROACH_FINAL_MAX_ALTITUDE_AGL and hAGL < APPROACH_MIN_ALTITUDE_AGL and i < self.dataLength:
    #                 airplaneMSL = self.flightData[i]['msl_altitude']
    #                 hAGL = airplaneMSL - airport.alt
    #                 i += 1

    #             # Decrement by 1 so that we are guaranteed that i < dataLength
    #             start = i - 1

    #             airplaneHdg = self.flightData[start]['heading']
    #             airplanePoint = self.flightData[start]['LatLon']

    #             runway = self.detectRunway(airplanePoint, airplaneHdg, airport)

    #             print("Runway:", "Unknown" if runway is None else runway.runwayCode)

    #             temp_list = []
    #             allValues = [ [], [], [], [] ]
    #             unstableReasons = [ [], [], [], [] ]  # F1, F2, A, S
    #             while distance < APPROACH_MIN_DISTANCE and hAGL <= APPROACH_FINAL_MAX_ALTITUDE_AGL and hAGL >= APPROACH_FINAL_MIN_ALTITUDE_AGL and i < self.dataLength:
    #                 airplaneHdg = self.flightData[i]['heading']
    #                 airplaneIAS = self.flightData[i]['indicated_airspeed']
    #                 airplaneVSI = self.flightData[i]['vertical_airspeed']

    #                 if runway is not None:
    #                     headingError = 180 - abs(abs(runway.magHeading - airplaneHdg) - 180)
    #                     cond_F1 = headingError <= APPROACH_MAX_HEADING_ERROR
    #                     crossTrackError = self.crossTrackToCenterLine(airplanePoint, runway)
    #                     cond_F2 = abs(crossTrackError) <= APPROACH_MAX_CROSSTRACK_ERROR
    #                 else:
    #                     cond_F1 = cond_F2 = True

    #                 cond_A = airplaneIAS >= APPROACH_MIN_IAS and airplaneIAS <= APPROACH_MAX_IAS
    #                 cond_S = airplaneVSI >= APPROACH_MIN_VSI

    #                 # Check to see if any parameters went unstable.
    #                 # if a condition is false, that means it was unstable
    #                 airplaneIsUnstable = not (cond_F1 and cond_F2 and cond_A and cond_S)

    #                 if airplaneIsUnstable:
    #                     print("F1=%s, F2=%s, A=%s, S=%s" % (cond_F1, cond_F2, cond_A, cond_S))
    #                     if not cond_F1:
    #                         print("\tRunway Heading: %s" % runway.magHeading)
    #                         print("\tAirplane Heading: %s" % airplaneHdg)
    #                         unstableReasons[0].append(headingError)
    #                     if not cond_F2:
    #                         print("\tCrossTrackToCenterLine: %s" % crossTrackError)
    #                         unstableReasons[1].append(crossTrackError)
    #                     if not cond_A:
    #                         print("\tIndicated Airspeed: %s knots" % (airplaneIAS))
    #                         unstableReasons[2].append(airplaneIAS)
    #                     if not cond_S:
    #                         print("\tVertical Airspeed: %s ft/min" % (airplaneVSI))
    #                         unstableReasons[3].append(airplaneVSI)
    #                     temp_list.append(i)
    #                 elif len(temp_list) > 0:
    #                     self._approaches[thisApproachID]['unstable'].append( (temp_list[0], temp_list[-1]) )
    #                     del temp_list[:]

    #                 # Including the parameter values whether the approach is
    #                 # stable or unstable for being able to do comparisons with
    #                 # the parameter distributions
    #                 if runway is not None:
    #                     allValues[0].append(headingError)
    #                     allValues[1].append(crossTrackError)
    #                 allValues[2].append(airplaneIAS)
    #                 allValues[3].append(airplaneVSI)

    #                 airplaneMSL = self.flightData[i]['msl_altitude']
    #                 airplanePoint = self.flightData[i]['LatLon']
    #                 distance = airplanePoint.distanceTo(airport.centerLatLon, EARTH_RADIUS_MILES)
    #                 hAGL = airplaneMSL - airport.alt

    #                 i += 1

    #             end = start if start == i - 1 else i - 1

    #             if len(temp_list) > 0:
    #                 self._approaches[thisApproachID]['unstable'].append( (temp_list[0], temp_list[-1]) )

    #             self._approaches[thisApproachID]['airport-code'] = airport.code
    #             self._approaches[thisApproachID]['runway-code'] = None if runway is None else runway.runwayCode
    #             self._approaches[thisApproachID]['approach-start'] = start
    #             self._approaches[thisApproachID]['approach-end'] = end
    #             self._approaches[thisApproachID]['F1'] = unstableReasons[0]
    #             self._approaches[thisApproachID]['F2'] = unstableReasons[1]
    #             self._approaches[thisApproachID]['A'] = unstableReasons[2]
    #             self._approaches[thisApproachID]['S'] = unstableReasons[3]
    #             self._approaches[thisApproachID]['HDG'] = allValues[0]
    #             self._approaches[thisApproachID]['CTR'] = allValues[1]
    #             self._approaches[thisApproachID]['IAS'] = allValues[2]
    #             self._approaches[thisApproachID]['VSI'] = allValues[3]

    #             i = self.analyzeLanding(end, airport, thisApproachID)

    #         i += 15

    def _analyze_single_approach(self, data_slice, airport, runway, approach_id):
        pass

    def _analyze_landing(self, idx_start, airport, approach_id):
        idx_end = (
            self._flight_data.loc[idx_start:, 'radio_altitude_derived'] >= APPROACH_MIN_ALTITUDE_AGL
        ).idxmax()

        # If idx_end == idx_start, that means the condition above was False for
        # the rest of the dataframe. Thus, we'll assign it the last index.
        if idx_end == idx_start:
            idx_end = len(self._flight_data.index) - 1

        landing_data_slice = self._flight_data.iloc[idx_start : idx_end+1]

        full_stop = (
            landing_data_slice['indicated_airspeed'] <= FULL_STOP_SPEED_INDICATOR
        ).any()

        AGL_WINDOW_SECONDS = 5

        agl_5_sec_windows = rolling_window(
            landing_data_slice['radio_altitude_derived'], AGL_WINDOW_SECONDS
        )
        touch_and_go = (
            np.average(agl_5_sec_windows, axis=1) < TOUCH_AND_GO_ELEVATION_INDICATOR
        ).any()

        if full_stop:
            self._approaches[approach_id]['landing-type'] = LandingResult['STOP_AND_GO'].value
            print("Full Stop!!!!")
        elif touch_and_go:
            self._approaches[approach_id]['landing-type'] = LandingResult['TOUCH_AND_GO'].value
            print("Touch and Go!!!!")
        else:
            self._approaches[approach_id]['landing-type'] = LandingResult['GO_AROUND'].value
            print("Go Around?!?!?!")

        self._approaches[approach_id]['landing-start'] = idx_start
        self._approaches[approach_id]['landing-end'] = idx_end
        print("")

        return idx_end


    # def _analyzeLanding(self, start, airport, thisApproachID):
    #     '''
    #     This function will analyze the time after the final approach and before the plane reaches a height of 150 feet (or until the flight ends if it is the final landing).
    #     @param: start the time index when the approach ends and the landing begins.
    #     @param: airport the airport that the airplane is attempting to land at
    #     @author: Wyatt Hedrick
    #     '''
    #     i = start
    #     airplaneMSL = self.flightData[i]['msl_altitude']
    #     hAGL = airplaneMSL - airport.alt
    #     elevations = []
    #     avgElevation = TOUCH_AND_GO_ELEVATION_INDICATOR + 1

    #     fullStop = touchAndGo = False

    #     while hAGL < APPROACH_MIN_ALTITUDE_AGL and i < self.dataLength - 1:
    #         if not fullStop:
    #             airplaneIAS = self.flightData[i]['indicated_airspeed']
    #             if airplaneIAS <= FULL_STOP_SPEED_INDICATOR:
    #                 fullStop = True
    #             elif avgElevation <= TOUCH_AND_GO_ELEVATION_INDICATOR:
    #                 touchAndGo = True

    #         i += 1
    #         airplaneMSL = self.flightData[i]['msl_altitude']
    #         hAGL = airplaneMSL - airport.alt

    #         if len(elevations) < 5:
    #             elevations.append(hAGL)
    #         else:
    #             elevations.pop(0)
    #             elevations.append(hAGL)
    #             avgElevation = sum(elevations) / len(elevations)

    #     end = i

    #     if fullStop:
    #         self._approaches[thisApproachID]['landing-type'] = 'stop-and-go'
    #         print("Full Stop!!!!")
    #     elif touchAndGo:
    #         self._approaches[thisApproachID]['landing-type'] = 'touch-and-go'
    #         print("Touch and Go!!!!")
    #     else:
    #         self._approaches[thisApproachID]['landing-type'] = 'go-around'
    #         print("Go Around?!?!?!")

    #     self._approaches[thisApproachID]['landing-start'] = start
    #     self._approaches[thisApproachID]['landing-end'] = end
    #     print("")

    #     return end

    def _crossTrackToCenterLine(self, airplanePoint, runway):
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

    # def _detectAirport(self, airplanePoint):
    #     '''
    #     This function detects the airport that is closest to the passed in coordinates.
    #     It performs this by scanning the airportData dictionary and calculating which
    #         airport as the lowest total difference between lat/lon.
    #     @param: lat the latitude of the plane
    #     @param: lon the longitude of the plane
    #     @author: Wyatt Hedrick
    #     '''
    #     ourAirport = None
    #     closestDifference = 0
    #     for key, airport in self.airports.items():
    #         dLat = abs(airport.centerLatLon.lat - airplanePoint.lat)  # getting difference in lat and lon
    #         dLon = abs(airport.centerLatLon.lon - airplanePoint.lon)
    #         totalDifference = dLat + dLon  # adding the differences so we can compare and see which airport is the closest
    #         if ourAirport is None or totalDifference < closestDifference:  # if it is the first time or we found a closer airport
    #             ourAirport = airport
    #             closestDifference = totalDifference

    #     return ourAirport

    def _detectRunway(self, airplanePoint, airplaneHdg, airport):
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

    def _outputToDB(self):
        '''
        Outputs the approach analysis information to the approaches table
            within the database.
        @return: None
        @author: Kelton Karboviak
        '''
        values = []
        for id, approach in self._approaches.items():
            valuesTup = (
                self._flight_id,
                id + 1,
                approach['airport-code'],
                approach['runway-code'],
                approach['approach-start'],
                approach['approach-end'],
                approach['landing-start'],
                approach['landing-end'],
                approach['landing-type'],
                int(approach['unstable']),
                None if not len(approach['HDG']) else np.average(approach['HDG']),
                None if not len(approach['F1']) else np.average(approach['F1']),
                None if not len(approach['CTR']) else np.average(approach['CTR']),
                None if not len(approach['F2']) else np.average(approach['F2']),
                None if not len(approach['IAS']) else np.average(approach['IAS']),
                None if not len(approach['A']) else np.average(approach['A']),
                None if not len(approach['VSI']) else np.average(approach['VSI']),
                None if not len(approach['S']) else np.average(approach['S']),
            )
            values.append(valuesTup)

        print('\n'.join(str(tup) for tup in values))

        if self._skip_output_to_db:
            return

        try:
            if len(values):  # Check to see if flight has any approaches to insert
                self._cursor.executemany(INSERT_SQL, values)
            self._cursor.execute(UPDATE_ANALYSES_SQL, (self.flightID,))
            self._db.commit()
        except mysql.Error as e:
            print("MySQL Error [%d]: %s\n" % (e.args[0], e.args[1]))
            print("Last Executed Query: ", self._cursor._last_executed)
            self._db.rollback()
