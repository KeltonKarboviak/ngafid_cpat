# -*- coding: utf-8 -*-

from enum import Enum
from typing import Dict, Tuple

import MySQLdb as mysql
import numpy as np
import pandas as pd
from numpy import absolute

from geoutils import (
    signed_heading_difference,
    unsigned_heading_difference,
    vincenty_distance,
)
from latlon import LatLon
from quad_tree import QuadTree
from runway import Runway


''' GLOBAL EXCEEDANCE THRESHOLDS '''
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

MILES_TO_FEET = 5280
AGL_WINDOW_SECONDS = 5
EARTH_RADIUS_MILES = 3959
EARTH_RADIUS_FEET = 20900000

SELECT_THRESHOLDS_SQL = """\
    SELECT * FROM exceedance_thresholds WHERE aircraft_id = %s;
"""

INSERT_KEYS_LIST = [
    'flight_id', 'approach_id', 'airport_id', 'runway_id',
    'approach_start', 'approach_end', 'landing_start', 'landing_end',
    'landing_type', 'unstable', 'all_heading', 'f1_heading',
    'all_crosstrack', "f2_crosstrack", 'all_ias', 'a_ias', 'all_vsi', 's_vsi',
]
INSERT_KEYS_SQL = ', '.join(INSERT_KEYS_LIST)
INSERT_UPDATE_VALUES_SQL = ', '.join(
    "{0}=VALUES({0})".format(key) for key in INSERT_KEYS_LIST
)
INSERT_VALUES_PLACEHOLDERS = ', '.join(["%s"] * len(INSERT_KEYS_LIST))
INSERT_SQL = """\
    INSERT INTO approaches (%s) VALUES (%s) ON DUPLICATE KEY UPDATE %s;
""" % (INSERT_KEYS_SQL, INSERT_VALUES_PLACEHOLDERS, INSERT_UPDATE_VALUES_SQL)

UPDATE_ANALYSES_SQL = """\
    UPDATE flight_analyses SET approach_analysis = 1 WHERE flight_id = %s;
"""

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

    def __init__(
        self,
        db: mysql.Connection,
        quad_tree: QuadTree,
        skip_output: bool = False
    ):
        self._db = db
        self._cursor = db.cursor(mysql.cursors.DictCursor)
        self._quad_tree = quad_tree
        self._skip_output_to_db = skip_output

        self._takeoffs = {}
        self._approaches = {}
        self._approach_id = 0

        self.vector_get_nearest_airports = np.vectorize(
            self._quad_tree.get_nearest_airport
        )
        self.vector_cross_track_distance = np.vectorize(
            self._cross_track_to_center_line
        )

    def analyze(
        self,
        flight_id: int,
        aircraft_type_id: int,
        data: pd.DataFrame,
        skip_analysis: bool = False
    ) -> Tuple[Dict[int, dict], Dict[int, dict]]:
        self._flight_id = flight_id

        self._flight_data = self._derive_necessary_data(data)
        self._data_length = len(data.index)

        if not skip_analysis and self._data_length > 0:
            # self._set_thresholds(aircraft_type_id)
            start = self._find_initial_takeoff()
            self._analyze_approaches(start)

        # if not self.skipOutputToDB:
        self._output_to_db()

        # Reset global variables for next analysis
        self._clear_approaches()
        self._reset_approach_id()

        # Return the dict of approaches
        return self._takeoffs, self._approaches

    def _derive_necessary_data(self, df: pd.DataFrame) -> pd.DataFrame:
        # Get airport that is closest to each point
        airplane_data = df[['latitude', 'longitude']].T.values
        df.loc[:, 'airport'] = self.vector_get_nearest_airports(
            *airplane_data
        )

        # Get distance from airplane to closest airport at each point
        airports = df['airport'].values
        airport_data = (
            [a.centerLatLon.lat for a in airports],
            [a.centerLatLon.lon for a in airports],
        )
        df.loc[:, 'distance'] = vincenty_distance(
            *airplane_data, *airport_data
        ) * MILES_TO_FEET

        # Get AGL at each point
        if 'radio_altitude_derived' not in df.columns:
            df.loc[:, 'radio_altitude_derived'] = (
                airplane_data[2] - airport_data[2]
            )

        return df

    def _set_thresholds(self, aircraft_type_id: int):
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
        TOUCH_AND_GO_ELEVATION_INDICATOR = row[
            'touch_and_go_elevation_indicator'
        ]
        RUNWAY_SELECTION_INDICATOR = row['runway_selection_indicator']

    def _clear_takeoffs(self):
        self._takeoffs.clear()

    def _clear_approaches(self):
        self._approaches.clear()

    def _reset_approach_id(self):
        self._approach_id = 0

    def _get_and_increment_approach_id(self) -> int:
        next_id, self._approach_id = self._approach_id, self._approach_id + 1

        return next_id

    def _find_initial_takeoff(self) -> int:
        # This will return the first index where the condition is True
        return (
            self._flight_data['radio_altitude_derived']
            >= APPROACH_MIN_ALTITUDE_AGL
        ).idxmax()

    def _analyze_approaches(self, idx_takeoff_end: int):
        try:
            # We'll loop until we go out of bounds on self._flight_data (see the
            # except block).
            while idx_takeoff_end < len(self._flight_data.index) - 1:
                mask_within_mile_below_500_ft = (
                    (
                        self._flight_data.loc[idx_takeoff_end:, 'distance']
                        < 5280
                    ) & (
                        self._flight_data.loc[
                            idx_takeoff_end:, 'radio_altitude_derived'
                        ] < APPROACH_MIN_ALTITUDE_AGL
                    )
                )
                idx_approach_attempt = mask_within_mile_below_500_ft.idxmax()

                airport = self._flight_data.loc[idx_approach_attempt, 'airport']

                print(
                    'Airplane is approaching {}, {}: {}'.format(
                        airport.city, airport.state, airport.code
                    )
                )

                approach_id = self._get_and_increment_approach_id()
                self._approaches[approach_id] = {}

                mask_not_between_150_500_ft_agl = ~self._flight_data.loc[
                    idx_approach_attempt:, 'radio_altitude_derived'
                ].between(
                    APPROACH_FINAL_MAX_ALTITUDE_AGL,
                    APPROACH_MIN_ALTITUDE_AGL,
                    inclusive=False
                )
                idx_start = mask_not_between_150_500_ft_agl.idxmax()

                runway = self._detect_runway(
                    *self._flight_data.loc[
                        idx_start, ['LatLon', 'heading']
                    ].values,
                    airport=airport
                )

                mask_not_within_mile_between_50_150_ft = ~(
                    (self._flight_data.loc[idx_start:, 'distance'] < 5280)
                    & (
                        self._flight_data.loc[
                            idx_start:, 'radio_altitude_derived'
                        ].between(
                            APPROACH_FINAL_MIN_ALTITUDE_AGL,
                            APPROACH_FINAL_MAX_ALTITUDE_AGL,
                            inclusive=True
                        )
                    )
                )
                idx_end = mask_not_within_mile_between_50_150_ft.idxmax()

                approach_data_slice = self._flight_data.iloc[
                    idx_start : idx_end+1
                ]

                self._analyze_single_approach(
                    approach_data_slice, airport, runway, approach_id
                )

                # Perform parameter analyses
                all_values = [[], [], [], []]
                unstable_reasons = [[], [], [], []]
                airplane_is_unstable = False

                if len(approach_data_slice.index):
                    # If the slice of data isn't empty
                    if runway is not None:
                        heading_errors = signed_heading_difference(
                            runway.magHeading,
                            approach_data_slice['heading'].values
                        )
                        cond_f1 = (
                            absolute(heading_errors)
                            <= APPROACH_MAX_HEADING_ERROR
                        )

                        cross_track_errors = self.vector_cross_track_distance(
                            approach_data_slice['LatLon'], runway
                        )
                        cond_f2 = (
                            absolute(cross_track_errors)
                            <= APPROACH_MAX_CROSSTRACK_ERROR
                        )
                    else:
                        cond_f1 = cond_f2 = np.full_like(
                            approach_data_slice.index, True
                        )

                    cond_a = approach_data_slice['indicated_airspeed'].between(
                        APPROACH_MIN_IAS, APPROACH_MAX_IAS, inclusive=True
                    ).values
                    cond_s = (
                        approach_data_slice['vertical_airspeed'].values
                        >= APPROACH_MIN_VSI
                    )

                    # Check to see if any parameters went unstable.
                    # if a condition is false, that means it was unstable
                    airplane_is_unstable = not (
                        cond_f1 & cond_f2 & cond_a & cond_s
                    ).all()

                    # Get unstable parameter values
                    # For each param, check if there was at least 1 unstable
                    # parameter instance. If so, then we'll grab only the
                    # values from the slice that failed the condition
                    if not cond_f1.all():
                        unstable_reasons[0] = heading_errors[~cond_f1]
                    if not cond_f2.all():
                        unstable_reasons[1] = cross_track_errors[~cond_f2]
                    if not cond_a.all():
                        unstable_reasons[2] = (
                            approach_data_slice['indicated_airspeed'].values[
                                ~cond_a
                            ]
                        )
                    if not cond_s.all():
                        unstable_reasons[3] = (
                            approach_data_slice['vertical_airspeed'].values[
                                ~cond_s
                            ]
                        )

                    # Get all parameter values in the approach (stable or
                    # unstable)
                    if runway is not None:
                        all_values[0] = heading_errors
                        all_values[1] = cross_track_errors
                    all_values[2] = (
                        approach_data_slice['indicated_airspeed'].values
                    )
                    all_values[3] = (
                        approach_data_slice['vertical_airspeed'].values
                    )

                self._approaches[approach_id]['airport-code'] = airport.code
                self._approaches[approach_id]['runway-code'] = (
                    None if runway is None else runway.runwayCode
                )
                self._approaches[approach_id]['approach-start'] = idx_start
                self._approaches[approach_id]['approach-end'] = idx_end
                self._approaches[approach_id]['unstable'] = (
                    airplane_is_unstable
                )
                self._approaches[approach_id]['F1'] = unstable_reasons[0]
                self._approaches[approach_id]['F2'] = unstable_reasons[1]
                self._approaches[approach_id]['A'] = unstable_reasons[2]
                self._approaches[approach_id]['S'] = unstable_reasons[3]
                self._approaches[approach_id]['HDG'] = all_values[0]
                self._approaches[approach_id]['CTR'] = all_values[1]
                self._approaches[approach_id]['IAS'] = all_values[2]
                self._approaches[approach_id]['VSI'] = all_values[3]

                idx_takeoff_end = self._analyze_landing(
                    idx_end, approach_id
                )
        except (KeyError, IndexError):
            # We went out of bounds on an index in self._flight_data, which
            # means we've gone through all the data. Thus, return out of
            # function.
            print('Hit the except block!!!')  # TODO: remove after testing
            return

    def _analyze_single_approach(
        self,
        data_slice,
        airport,
        runway,
        approach_id
    ):
        pass

    def _analyze_landing(self, idx_start, approach_id):
        idx_end = (
            self._flight_data.loc[idx_start:, 'radio_altitude_derived']
            >= APPROACH_MIN_ALTITUDE_AGL
        ).idxmax()

        # If idx_end == idx_start, that means the condition above was False for
        # the rest of the dataframe. Thus, we'll assign it the last index.
        if idx_end == idx_start:
            idx_end = len(self._flight_data.index) - 1

        landing_data_slice = self._flight_data.iloc[idx_start : idx_end+1]

        full_stop = (
            landing_data_slice['indicated_airspeed']
            <= FULL_STOP_SPEED_INDICATOR
        ).any()

        agl_5_sec_windows = rolling_window(
            landing_data_slice['radio_altitude_derived'], AGL_WINDOW_SECONDS
        )
        touch_and_go = (
            np.average(agl_5_sec_windows, axis=1)
            < TOUCH_AND_GO_ELEVATION_INDICATOR
        ).any()

        landing_result = LandingResult[(
            'STOP_AND_GO'
            if full_stop
            else ('TOUCH_AND_GO' if touch_and_go else 'GO_AROUND')
        )]

        print(landing_result.value)

        self._approaches[approach_id]['landing-type'] = landing_result.value
        self._approaches[approach_id]['landing-start'] = idx_start
        self._approaches[approach_id]['landing-end'] = idx_end
        print('')

        return idx_end

    @staticmethod
    def _cross_track_to_center_line(
        airplane_point: LatLon,
        runway: Runway
    ) -> float:
        return airplane_point.cross_track_distance_to(
            runway.centerLatLon, runway.trueHeading, EARTH_RADIUS_FEET
        )

    @staticmethod
    def _detect_runway(airplane_point, airplane_hdg, airport):
        our_runway = None
        closest_difference = 0
        for runway in airport.runways:
            if (
                unsigned_heading_difference(runway.magHeading, airplane_hdg)
                <= RUNWAY_SELECTION_INDICATOR
            ):
                d_lat = abs(runway.centerLatLon.lat - airplane_point.lat)
                d_lon = abs(runway.centerLatLon.lon - airplane_point.lon)
                total_difference = d_lat + d_lon

                if our_runway is None or total_difference < closest_difference:
                    our_runway = runway
                    closest_difference = total_difference

        return our_runway

    def _output_to_db(self):
        values = [
            (
                self._flight_id,
                approach_id + 1,
                approach['airport-code'],
                approach['runway-code'],
                approach['approach-start'],
                approach['approach-end'],
                approach['landing-start'],
                approach['landing-end'],
                approach['landing-type'],
                int(approach['unstable']),
                np.average(approach['HDG']) if len(approach['HDG']) else None,
                np.average(approach['F1']) if len(approach['F1']) else None,
                np.average(approach['CTR']) if len(approach['CTR']) else None,
                np.average(approach['F2']) if len(approach['F2']) else None,
                np.average(approach['IAS']) if len(approach['IAS']) else None,
                np.average(approach['A']) if len(approach['A']) else None,
                np.average(approach['VSI']) if len(approach['VSI']) else None,
                np.average(approach['S']) if len(approach['S']) else None,
            )
            for approach_id, approach in self._approaches.items()
        ]

        print('\n'.join(str(tup) for tup in values))

        if self._skip_output_to_db:
            return

        try:
            if len(values):
                # Check to see if flight has any approaches to insert
                self._cursor.executemany(INSERT_SQL, values)
            self._cursor.execute(UPDATE_ANALYSES_SQL, (self._flight_id,))
            self._db.commit()
        except mysql.Error as e:
            print("MySQL Error [%d]: %s\n" % (e.args[0], e.args[1]))
            print("Last Executed Query: ", self._cursor._last_executed)
            self._db.rollback()
