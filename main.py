#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function

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
from latlon import LatLon
from runway import Runway
from config import db_credentials
from flight_analyzer import FlightAnalyzer
from quad_tree import QuadTree


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
    SELECT id, name, city, state_code, latitude, longitude, elevation
    FROM test_airports;
"""
fetchRunwayDataSQL = """\
    SELECT
        airport_id, id, touchdown_lat, touchdown_lon, tdze, magnetic_course,
        true_course
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
        eng_1_rpm
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
        airports[runway['airport_id']].addRunway(Runway(
            runway['airport_id'],
            runway['tdze'],
            runway['id'],
            runway['magnetic_course'],
            runway['true_course'],
            runway['touchdown_lat'],
            runway['touchdown_lon']
        ))


# def loadAirportData():
#     """
#     Populate a dictionary containing airport data for all airports throughout the U.S.
#     @author: Wyatt Hedrick
#     """
#     with open('data/Airports.csv', 'r') as infile:
#         infile.readline()  # Trash line of data headers
#         for line in infile:
#             row = line.split(',')
#             #             code,   name,   city,  state,      latitude,     longitude,      altitude
#             a = Airport(row[0], row[1], row[2], row[3], float(row[4]), float(row[5]), float(row[6]))
#             airports[row[0]] = a  # Insert into airports dict with airportCode as key
#     with open('data/AirportsDetailed.csv', 'r') as infile:
#         infile.readline()  # Trash line of data headers
#         for line in infile:
#             row = line.split(',')
#             #     airportCode,      altitude, runwayCode,      magHdg,        trueHdg,      centerLat,      centerLon
#             r = Runway(row[2], float(row[6]), row[10], float(row[11]), float(row[12]), float(row[25]), float(row[26]))
#             airports[row[2]].addRunway(r)  # Add runway to corresponding airport


def main(flight_ids, run_multi_process, skip_output):
    global db, cursor, airports, quad_tree, analyzer

    # If there are no flight_ids passed as command-line args,
    # fetch all flights that haven't been analyzed for approaches yet
    # Otherwise the ids passed into argv will only be analyzed
    if len(flight_ids) == 0:
        cursor.execute(fetchFlightIDsSQL)
        flights = cursor.fetchall()
        flight_ids = [flight['flight_id'] for flight in flights]

    logger.info('Number of Flights to Analyze: %4d', len(flight_ids))

    with stopwatch('Loading Airport Data'):
        airports = load_airport_data()
        load_runway_data_into_airports()

    with stopwatch('Loading Quad Tree'):
        # Load Airports into a QuadTree
        quad_tree = QuadTree()
        for k, v in airports.items():
            quad_tree.insert(v)

    analyzer = FlightAnalyzer(db, quad_tree, skip_output)

    for flight_id in flight_ids:
        logger.info('Processing Starting for Flight ID [%s]', flight_id)
        try:
            aircraft_type_id = get_aircraft_type(flight_id)
            flight_data = get_flight_data(flight_id)

            analyzer.analyze(flight_id, aircraft_type_id, flight_data)
        except mysql.Error as e:
            logger.exception('MySQL Error [%d]: %s', e.args[0], e.args[1])
            logger.exception('Last Executed Query: %s', cursor._last_executed)
        except pd.io.sql.DatabaseError as e:
            logger.exception('Pandas Error: %s', e)

        logger.info('Processing Complete for Flight ID [%s]', flight_id)

        break  # Temporary so that only one flight is processed


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
        '-m', '--multi-process',
        action='store_true',
        help='run program with multiple processes'
    )
    parser.add_argument(
        '--no-write',
        action='store_true',
        help='program will not save results to DB'
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
