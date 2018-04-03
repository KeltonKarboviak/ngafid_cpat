# -*- coding: utf-8 -*-

from __future__ import print_function

from collections import namedtuple
from enum import Enum
from typing import Dict, Tuple, Optional

import MySQLdb as mysql
import numpy as np
import pandas as pd
from numpy import absolute

from airport import Airport
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

CROSS_TRACK_LEVEL_1_ERROR = 25  # feet
CROSS_TRACK_LEVEL_2_ERROR = 100  # feet

TURN_START_DEGREES = 90
TURN_END_DEGREES = 15

MILES_TO_FEET = 5280
AGL_WINDOW_SECONDS = 5
EARTH_RADIUS_MILES = 3959
EARTH_RADIUS_FEET = 20900000

SELECT_THRESHOLDS_SQL = """\
    SELECT * FROM exceedance_thresholds WHERE aircraft_id = %s;
"""

INSERT_KEYS_LIST = [
    'flight_id', 'approach_id', 'airport_id', 'runway_id',
    'turn_start', 'turn_end', 'turn_error_severity', 'turn_error_type',
    'approach_start', 'approach_end', 'landing_start', 'landing_end',
    'landing_type', 'unstable', 'all_heading', 'f1_heading', 'all_crosstrack',
    "f2_crosstrack", 'all_ias', 'a_ias', 'all_vsi', 's_vsi',
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

LandingAnalysisResult = namedtuple(
    'LandingAnalysisResult', 'is_followed_by_takeoff idx_landing_end'
)


def rolling_window(a, window):
    if len(a) < window:
        # If array does not have at least `window` number of elements, then
        # return a 2D array with a single NAN
        return np.array([[np.nan]])

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
        self._takeoff_id = 0
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
            # start = self._find_initial_takeoff()
            # self._analyze_approach(start)
            self._analyze()

        # if not self.skipOutputToDB:
        self._output_to_db()

        takeoffs, approaches = self._takeoffs.copy(), self._approaches.copy()

        # Reset global variables for next analysis
        self._clear_takeoffs()
        self._reset_takeoff_id()
        self._clear_approaches()
        self._reset_approach_id()

        # Return the dicts of takeoffs & approaches
        return takeoffs, approaches

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

    def _reset_takeoff_id(self):
        self._takeoff_id = 0

    def _reset_approach_id(self):
        self._approach_id = 0

    def _get_and_increment_approach_id(self) -> int:
        next_id, self._approach_id = self._approach_id, self._approach_id + 1

        return next_id

    def _analyze(self):
        idx_takeoff_start, idx_takeoff_end, is_followed_by_takeoff = 0, 0, True

        try:
            while idx_takeoff_start < self._flight_data.index[-1]:
                if is_followed_by_takeoff:
                    idx_takeoff_end = self._analyze_takeoff(idx_takeoff_start)
                    self._takeoff_id += 1
                else:
                    idx_takeoff_end = idx_takeoff_start

                idx_approach_end = self._analyze_approach(idx_takeoff_end)

                landing_results = self._analyze_landing(idx_approach_end)
                is_followed_by_takeoff, idx_takeoff_start = (
                    landing_results.is_followed_by_takeoff,
                    landing_results.idx_landing_end
                )
                self._approach_id += 1
        except (KeyError, IndexError):
            # We went out of bounds on an index in self._flight_data, which
            # means we've gone through all the data. Thus, return out of
            # function.
            print('Hit the except block!!!')  # TODO: remove after testing

    def _analyze_takeoff(self, idx_takeoff_start: int) -> int:
        """
        Analyzes a single takeoff that begins at index 'idx_takeoff_start'.
        This will perform stability analysis and store its results in
        self._takeoffs.
        :param idx_takeoff_start: Index at which the takeoff begins
        :return: Index at which the takeoff ends (aircraft goes above
        APPROACH_MIN_ALTITUDE_AGL).
        """
        # This will return the first index where the condition is True
        mask_above_500_ft = (
            self._flight_data.loc[idx_takeoff_start:, 'radio_altitude_derived']
            > APPROACH_MIN_ALTITUDE_AGL
        )

        if not mask_above_500_ft.any():
            # If all of the entries in the mask are False, that means there
            # is not a takeoff for the rest of the data (which means
            # something weird happened).  Therefore, we'll just return the
            # last index of the data + 1 to stop all analysis from happening.
            return self._flight_data.index[-1] + 1

        idx_takeoff_end = mask_above_500_ft.idxmax()

        # TODO: do analysis
        takeoff_data_slice = self._flight_data.iloc[
            idx_takeoff_start : idx_takeoff_end+1
        ]

        airport = takeoff_data_slice.loc[idx_takeoff_start, 'airport']
        runway = self._detect_runway(
            *takeoff_data_slice.loc[
                idx_takeoff_start, ['LatLon', 'heading']
            ].values,
            airport=airport
        )

        speeds = takeoff_data_slice['indicated_airspeed']
        speed_diffs = speeds.diff()
        m = speed_diffs < 0

        # TODO: store analysis
        takeoff_id = self._takeoff_id
        self._takeoffs[takeoff_id] = {
            'airport-id': airport.id,
            'runway-id': None if runway is None else runway.id,
            'speed-diffs': speed_diffs[m],
            'agl': takeoff_data_slice.loc[m, 'radio_altitude_derived']
        }

        return idx_takeoff_end

    def _analyze_approach(self, idx_takeoff_end: int):
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

        if not mask_within_mile_below_500_ft.any():
            # If all entries in the mask are False, then that means there was
            # not another approach attempt for the rest of the data.
            # Therefore, we will return the last index in the data to signify
            # we've reached the end.
            return self._flight_data.index[-1]

        idx_approach_attempt = mask_within_mile_below_500_ft.idxmax()

        # Create a new dictionary to store the results of the current
        # approach
        self._approaches[self._approach_id] = {}

        airport = self._flight_data.loc[idx_approach_attempt, 'airport']

        print(
            'Airplane is approaching {}, {}: {}'.format(
                airport.city, airport.state, airport.code
            )
        )  # TODO: remove after testing

        mask_not_between_150_500_ft_agl = ~self._flight_data.loc[
            idx_approach_attempt:, 'radio_altitude_derived'
        ].between(
            APPROACH_FINAL_MAX_ALTITUDE_AGL,
            APPROACH_MIN_ALTITUDE_AGL,
            inclusive=False
        )
        idx_approach_start = mask_not_between_150_500_ft_agl.idxmax()

        mask_not_within_mile_between_50_150_ft = ~(
            (self._flight_data.loc[idx_approach_start:, 'distance'] < 5280)
            & (
                self._flight_data.loc[
                    idx_approach_start:, 'radio_altitude_derived'
                ].between(
                    APPROACH_FINAL_MIN_ALTITUDE_AGL,
                    APPROACH_FINAL_MAX_ALTITUDE_AGL,
                    inclusive=True
                )
            )
        )
        idx_approach_end = mask_not_within_mile_between_50_150_ft.idxmax()

        runway = self._detect_runway(
            *self._flight_data.loc[
                idx_approach_end, ['LatLon', 'heading']
            ].values,
            airport=airport
        )

        if runway is not None:
            idx_turn_start, idx_turn_end = self._find_turn_to_final(
                idx_approach_end, runway
            )

            # Check to see if a turn-to-final was actually performed
            if idx_turn_start is not None and idx_turn_end is not None:
                turn_severity, turn_type = self._analyze_turn_to_final(
                    idx_turn_start, idx_turn_end, runway
                )

                # If there was a turn-to-final, then we'll say that the
                # approach starts where the turn ends. This makes graphing
                # look continuous.
                idx_approach_start = max(idx_turn_end, idx_approach_start)
            else:
                turn_severity, turn_type = None, None
        else:
            # If we don't have the runway, then we'll set both the turn's start
            # & end to the index of the approach start, and None to the turn
            # details
            idx_turn_start, idx_turn_end, turn_severity, turn_type = (
                idx_approach_start, idx_approach_start, None, None
            )

        self._approaches[self._approach_id].update({
            'turn-start': idx_turn_start,
            'turn-end': idx_turn_end,
            'turn-error-severity': turn_severity,
            'turn-error-type': turn_type
        })

        approach_data_slice = self._flight_data.iloc[
            idx_approach_start: idx_approach_end + 1
        ]

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
                    approach_data_slice['indicated_airspeed'].values[~cond_a]
                )
            if not cond_s.all():
                unstable_reasons[3] = (
                    approach_data_slice['vertical_airspeed'].values[~cond_s]
                )

            # Get all parameter values in the approach (stable or
            # unstable)
            if runway is not None:
                all_values[0] = heading_errors
                all_values[1] = cross_track_errors

            all_values[2] = approach_data_slice['indicated_airspeed'].values
            all_values[3] = approach_data_slice['vertical_airspeed'].values

        self._approaches[self._approach_id].update({
            'airport-id': airport.id,
            'runway-id': None if runway is None else runway.id,
            'approach-start': idx_approach_start,
            'approach-end': idx_approach_end,
            'unstable': airplane_is_unstable,
            'F1': unstable_reasons[0],
            'F2': unstable_reasons[1],
            'A': unstable_reasons[2],
            'S': unstable_reasons[3],
            'HDG': all_values[0],
            'CTR': all_values[1],
            'IAS': all_values[2],
            'VSI': all_values[3],
        })

        return idx_approach_end

    def _find_turn_to_final(
        self,
        idx_approach_end: int,
        runway: Runway
    ) -> Tuple[int, int]:
        # Get last 3 minutes (180 seconds) of data before 'idx_approach_end'
        heading_series = self._flight_data.iloc[idx_approach_end-180 : idx_approach_end]['heading']
        heading_errors = pd.Series(
            unsigned_heading_difference(runway.magHeading, heading_series.values),
            index=heading_series.index
        )

        # We'll use this as the heading error indicator that the pilot is
        # beginning their turn-to-final. It will either be the minimum of
        # TURN_START_DEGREES or the maximum of the heading errors. The latter
        # value is used when the aircraft is never more than TURN_START_DEGREES
        # off of the runway heading.
        # turn_start_indicator = min(
        #     heading_errors.values.max(),
        #     TURN_START_DEGREES
        # )
        mask_hdg_error_geq_90_deg = (heading_errors[::-1] >= TURN_START_DEGREES)
        idx_turn_start = mask_hdg_error_geq_90_deg.idxmax()

        if not mask_hdg_error_geq_90_deg.any():
            # If there were not any heading errors >= 90 deg within the last
            # 3 mins, that means the aircraft performed a straight-in approach
            # and did not have a turn-to-final
            idx_turn_start, idx_turn_end = None, None
        else:
            idx_turn_end = (
                heading_errors.loc[:idx_turn_start:-1] >= TURN_END_DEGREES
            ).idxmax()

        return idx_turn_start, idx_turn_end

    def _analyze_turn_to_final(
        self,
        idx_turn_start: int,
        idx_turn_end: int,
        runway: Runway
    ) -> Tuple[Optional[str], str]:
        turn_data_slice = self._flight_data.iloc[
            idx_turn_start : idx_turn_end+1
        ]

        cross_track_error = self._cross_track_to_center_line(
            turn_data_slice.loc[idx_turn_end, 'LatLon'], runway
        )

        left_direction = abs(turn_data_slice['roll_attitude'].values.min())
        right_direction = abs(turn_data_slice['roll_attitude'].values.max())
        roll_direction = 'left' \
            if left_direction > right_direction \
            else 'right'

        abs_cross_track_error = abs(cross_track_error)
        if abs_cross_track_error > CROSS_TRACK_LEVEL_2_ERROR:
            severity = 'large'
        elif abs_cross_track_error > CROSS_TRACK_LEVEL_1_ERROR:
            severity = 'small'
        else:
            severity = None

        if severity is not None:
            if roll_direction == 'left':
                turn_error = 'undershoot' if cross_track_error < 0 else 'overshoot'
            else:
                turn_error = 'undershoot' if cross_track_error > 0 else 'overshoot'
        else:
            turn_error = 'aligned'

        return severity, turn_error

    def _analyze_landing(self, idx_landing_start: int) -> LandingAnalysisResult:
        if idx_landing_start == self._flight_data.index[-1]:
            # If we are given the last index of data as the landing start,
            # that means there was an issue in the approach analysis. So
            # we'll just return the same index as the landing's end so that
            # the analysis loop will stop.
            return LandingAnalysisResult(
                is_followed_by_takeoff=False,
                idx_landing_end=self._flight_data.index[-1]
            )

        mask_above_500_ft = (
            self._flight_data.loc[idx_landing_start:, 'radio_altitude_derived']
            >= APPROACH_MIN_ALTITUDE_AGL
        )

        # If there are not any True entries in the mask, that means the
        # condition above was False for the rest of the dataframe. Thus, we'll
        # assign it the last index.
        end_of_data = not mask_above_500_ft.any()

        if end_of_data:
            idx_landing_end = self._flight_data.index[-1]
        else:
            idx_landing_end = mask_above_500_ft.idxmax()

        landing_data_slice = self._flight_data.iloc[
            idx_landing_start : idx_landing_end+1
        ]

        full_stop = (
            landing_data_slice['indicated_airspeed']
            <= FULL_STOP_SPEED_INDICATOR
        ).any()

        agl_5_sec_windows = rolling_window(
            landing_data_slice['radio_altitude_derived'].values,
            AGL_WINDOW_SECONDS
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

        is_followed_by_takeoff = not (
            end_of_data or landing_result == LandingResult.GO_AROUND
        )

        if is_followed_by_takeoff:
            # Since this landing will be followed by a takeoff, we will find
            # the last index in which the minimum RPM value occurs. That point
            # marks that the pilot is transitioning from landing to takeoff.
            # We'll reset idx_landing_end to that point as well and store as
            # the landing's end.
            mask_takeoff_start = (landing_data_slice['eng_1_rpm'] > 2200) & (landing_data_slice['groundspeed'] > 25) & (landing_data_slice['indicated_airspeed'] > 0)
            idx_landing_end = mask_takeoff_start.idxmax()

            # min_rpm = landing_data_slice['eng_1_rpm'].values.min()
            # last_occurrence_of_min_rpm = landing_data_slice.loc[
            #     landing_data_slice['eng_1_rpm'] == min_rpm, 'eng_1_rpm'
            # ].idxmax()
            #
            # idx_landing_end = last_occurrence_of_min_rpm

        print(landing_result.value)  # TODO: remove after testing

        approach_id = self._approach_id
        self._approaches[approach_id].update({
            'landing-type': landing_result.value,
            'landing-start': idx_landing_start,
            'landing-end': idx_landing_end,
        })
        print('')  # TODO: remove after testing

        return LandingAnalysisResult(
            is_followed_by_takeoff=is_followed_by_takeoff,
            idx_landing_end=idx_landing_end
        )

    @staticmethod
    def _cross_track_to_center_line(
        airplane_point: LatLon,
        runway: Runway
    ) -> float:
        return airplane_point.cross_track_distance_to(
            runway.centerLatLon, runway.trueHeading, EARTH_RADIUS_FEET
        )

    @staticmethod
    def _detect_runway(
        airplane_point: LatLon,
        airplane_hdg: float,
        airport: Airport
    ) -> Runway:
        our_runway = None
        closest_difference = 10e6
        for runway in airport.runways:
            if (
                unsigned_heading_difference(runway.magHeading, airplane_hdg)
                <= RUNWAY_SELECTION_INDICATOR
            ):
                difference = airplane_point.distance_to(
                    runway.centerLatLon, EARTH_RADIUS_FEET
                )

                if difference < closest_difference:
                    our_runway = runway
                    closest_difference = difference

        return our_runway

    def _output_to_db(self):
        values = [
            (
                self._flight_id,
                approach_id + 1,
                approach['airport-id'],
                approach['runway-id'],
                approach['turn-start'],
                approach['turn-end'],
                approach['turn-error-severity'],
                approach['turn-error-type'],
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
