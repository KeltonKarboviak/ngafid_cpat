#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function

import json
import argparse
import contextlib
import logging
import multiprocessing
import time
from typing import Dict

import MySQLdb as mysql
import numpy as np
import pandas as pd

from airport import Airport
from config import db_credentials
from flight_analyzer import FlightAnalyzer
from latlon import LatLon
from quad_tree import QuadTree
from runway import Runway


""" LOGGING SETUP """
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(process)d - %(message)s"
)
logger = logging.getLogger(__file__)

""" IMPORT ENVIRONMENT-SPECIFIC CONFIGS """
ENV = "dev"
db_creds = db_credentials[ENV]

""" SQL STATEMENTS """
fetchAirportDataSQL = """\
    SELECT id, code, name, city, state_code, latitude, longitude, elevation
    FROM test_airports;
"""
fetchRunwayDataSQL = """\
    SELECT
        id, code, airport_id, touchdown_lat, touchdown_lon, tdze,
        magnetic_course, true_course
    FROM test_runways;
"""
fetchFlightIDsSQL = """\
    SELECT flight_id FROM flight_analyses WHERE approach_analysis = 0;
"""
fetchAircraftTypeSQL = 'SELECT aircraft_type FROM flight_id WHERE id = %s;'
fetchFlightDataSQL = """
    SELECT
        time, msl_altitude, radio_altitude_derived, indicated_airspeed,
        vertical_airspeed, heading, latitude, longitude, pitch_attitude,
        roll_attitude, eng_1_rpm
    FROM
        main
    WHERE
        flight = %s
    ORDER BY time ASC;
"""

""" GLOBAL VARIABLES """
db = None
cursor = None
analyzer = None
airports = {}
quad_tree = None
NUM_CPUS = multiprocessing.cpu_count()

vector_create_latlons = np.vectorize(lambda lat, lon: LatLon(lat, lon))


def get_aircraft_type(flight_id: int) -> int:
    cursor.execute(fetchAircraftTypeSQL, (flight_id,))

    return cursor.fetchone()['aircraft_type']


def get_flight_data(flight_id: int) -> pd.DataFrame:
    df = pd.read_sql(fetchFlightDataSQL, con=db, params=[flight_id])

    # Create LatLon objects by grabbing the lat,lon columns, transpose so
    # lat,lon becomes the rows, then unpack the numpy values array
    df.loc[:, 'LatLon'] = vector_create_latlons(
        *df[['latitude', 'longitude']].T.values
    )

    return df


def load_airport_data() -> Dict[str, Airport]:
    cursor.execute(fetchAirportDataSQL)

    return {
        airport['id']: Airport(
            airport['id'],
            airport['code'],
            airport['name'],
            airport['city'],
            airport['state_code'],
            airport['latitude'],
            airport['longitude'],
            airport['elevation']
        )
        for airport in cursor.fetchall()
    }


def load_runway_data_into_airports():
    global airports

    cursor.execute(fetchRunwayDataSQL)

    for runway in cursor.fetchall():
        airports[runway['airport_id']].add_runway(Runway(
            runway['id'],
            runway['airport_id'],
            runway['tdze'],
            runway['code'],
            runway['magnetic_course'],
            runway['true_course'],
            runway['touchdown_lat'],
            runway['touchdown_lon']
        ))


def main(flight_ids, run_multi_process, skip_output):
    global db, cursor, airports, quad_tree, analyzer

    # If there are no flight_ids passed as command-line args,
    # fetch all flights that haven't been analyzed for approaches yet
    # Otherwise the ids passed into argv will only be analyzed
    if len(flight_ids) == 0:
        # cursor.execute(fetchFlightIDsSQL)
        # flights = cursor.fetchall()
        # flight_ids = [flight['flight_id'] for flight in flights]
        flight_ids = (381046, 381218, 381233, 381349, 381812, 382172, 382178, 382486, 382496, 382538, 382741, 382928, 383219, 383403, 383544, 383556, 383749, 383781, 383790, 384269, 384270, 384307, 384326, 384412, 384420, 384441, 384445, 384460, 384476, 384647, 384674, 384965, 385012, 385331, 385645, 385690, 385836, 386486, 386666, 386765, 386800, 387160, 387181, 387201, 387607, 387627, 387765, 387949, 388186, 388192, 388354, 388498, 388638, 388639, 389027, 389165, 389178, 389421, 389521, 389844, 389850, 390048, 390052, 390082, 390131, 390247, 392334, 392504, 392538, 392706, 392824, 392836, 392886, 392898, 392955, 393046, 393230, 393246, 393289, 393554, 393655, 393769, 393837, 394127, 394355, 394362, 394365, 394475, 394645, 394766, 394927, 394933, 394998, 395219, 395220, 395316, 395374, 395599, 397800, 397803)

    logger.info('Number of Flights to Analyze: %4d', len(flight_ids))

    with stopwatch('Loading Airport & Runway Data'):
        airports = load_airport_data()
        load_runway_data_into_airports()

    with stopwatch('Loading Quad Tree'):
        # Load Airports into a QuadTree
        quad_tree = QuadTree()
        for k, v in airports.items():
            quad_tree.insert(v)

    analyzer = FlightAnalyzer(db, quad_tree, skip_output)

    values = {
        'HDG': [],
        'CTR': [],
        'IAS': [],
        'VSI': [],
    }

    for flight_id in flight_ids:
        logger.info('Processing Starting for Flight ID [%s]', flight_id)
        try:
            aircraft_type_id = get_aircraft_type(flight_id)
            flight_data = get_flight_data(flight_id)

            takeoffs, approaches = analyzer.analyze(
                flight_id, aircraft_type_id, flight_data
            )

            for i, a in approaches.items():
                for param in values.keys():
                    if a['landing-type'] != 'go-around':
                        if param == 'CTR' and (np.abs(a[param]) > 100).any():
                            with open('out.txt', 'a') as o:
                                o.write('(%s, %s) => (%s, %s) => (%f, %f) => (%s, %s)\n' % (flight_id, i, a['airport-id'], a['runway-id'], np.abs(a[param]).max(), np.average(a[param]), a['approach-start'], a['approach-end']))

                        values[param].extend(a[param])
        except mysql.Error as e:
            logger.exception('MySQL Error [%d]: %s', e.args[0], e.args[1])
            logger.exception('Last Executed Query: %s', cursor._last_executed)
        except pd.io.sql.DatabaseError as e:
            logger.exception('Pandas Error: %s', e)

        logger.info('Processing Complete for Flight ID [%s]', flight_id)

    with open('params.txt', 'w') as handle:
        json.dump(values, handle)


@contextlib.contextmanager
def stopwatch(msg):
    """ Context manager to print how long a block of code ran. """
    t0 = time.time()
    try:
        yield
    finally:
        t1 = time.time()
    print("Total elapsed time for %s: %.3f seconds" % (msg, t1 - t0))
    # logger.info("Total elapsed time for %s: %.3f seconds", msg, t1 - t0)


if __name__ == '__main__':
    # Parse command-line args
    parser = argparse.ArgumentParser(
        description='Tool to detect approaches in flight data.'
    )
    parser.add_argument(
        'flight_ids',
        metavar='flight_id',
        type=str,
        nargs='*',
        help='a Flight ID to be analyzed'
    )
    parser.add_argument(
        '--no-write',
        action='store_true',
        help='program will not save results to DB'
    )
    parser.add_argument(
        '-m', '--multi-process',
        action='store_true',
        help='run program with multiple processes'
    )
    args = parser.parse_args()

    try:
        db = mysql.connect(**db_creds)
        cursor = db.cursor(mysql.cursors.DictCursor)

        with stopwatch('Program Execution'):
            main(args.flight_ids, args.multi_process, args.no_write)
    except mysql.Error as e:
        logger.exception('MySQL Error [%d]: %s', e.args[0], e.args[1])
    finally:
        if cursor is not None:
            cursor.close()
        if db is not None:
            db.close()
