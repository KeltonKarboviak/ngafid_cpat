#!/usr/bin/env python

import argparse
import contextlib
import logging
import multiprocessing
import MySQLdb
import time
from Airport import Airport
from FlightAnalysis import FlightAnalyzer
from LatLon import LatLon
from Runway import Runway


""" LOGGING SETUP """
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(process)d - %(message)s")
logger = logging.getLogger(__name__)

""" IMPORT ENVIRONMENT-SPECIFIC CONFIGS """
ENV = "DEV"

if ENV == "DEV":
    import config.db_config_DEV as db_config
else:
    import config.db_config_PROD as db_config


""" SQL STATEMENTS """
# fetchAirportDataSQL = "SELECT AirportCode, AirportName, City, StateCode, Latitude, Longitude, Elevation FROM dev_fdm_test.airports;"
# fetchRunwayDataSQL = "SELECT AirportCode, Runway, tdze, magRunwayCourse, trueRunwayCourse, touchdownLat, touchdownLong FROM dev_fdm_test.airports_runways;"
fetchFlightIDsSQL = "SELECT flight_id FROM flight_analyses WHERE approach_analysis = 0;"
fetchAircraftTypeSQL = "SELECT aircraft_type FROM flight_id WHERE id = %s;"
fetchFlightDataSQL = '''
    SELECT
        time, msl_altitude, indicated_airspeed, vertical_airspeed, heading, latitude, longitude, pitch_attitude, eng_1_rpm
    FROM
        main
    WHERE
        flight = %s
    ORDER BY time ASC;
'''

""" GLOBAL VARIABLES """
globalConn = None
globalCursor = None
globalFlightAnalyzer = None
airports = {}
NUM_CPUS = multiprocessing.cpu_count()  # Set number of CPUs to use for multiprocessing


class Consumer(multiprocessing.Process):

    def __init__(self, task_queue, skipOutputToDB):
        multiprocessing.Process.__init__(self)
        self.task_queue = task_queue
        self.conn = MySQLdb.connect(**db_config.credentials)
        self.cursor = self.conn.cursor(MySQLdb.cursors.DictCursor)
        self.flightAnalyzer = FlightAnalyzer(self.conn, self.cursor, airports, skipOutput=skipOutputToDB)
    # end def __init__()

    def run(self):
        while True:
            next_task = self.task_queue.get()
            if next_task is None:
                print 'Tasks Complete! Exiting ...'
                self.task_queue.task_done()
                break
            answer = next_task(connection=self.conn, analyzer=self.flightAnalyzer)
            self.task_queue.task_done()
    # end def run()

# end class Consumer


class Task(object):

    def __init__(self, flightID):
        self.flightID = flightID
    # end def __init__()

    def __call__(self, connection=None, analyzer=None):
        logging.info("Now Analyzing Flight ID [%s]", self.flightID)

        cursor = connection.cursor(MySQLdb.cursors.DictCursor)

        try:
            cursor.execute(fetchAircraftTypeSQL, (self.flightID,))
            aircraftType = cursor.fetchone()['aircraft_type']

            # Get the flight's data
            cursor.execute(fetchFlightDataSQL, (self.flightID,))
            rows = cursor.fetchall()

            flightData = []
            for row in rows:
                # Before checking if flight data is valid, filter out data rows
                # that contain NULL values
                if None not in row.values():
                    row['LatLon'] = LatLon(row['latitude'], row['longitude'])
                    flightData.append(row)
            # end for

            approaches = analyzer.analyze(
                self.flightID,
                aircraftType,
                flightData,
                skipAnalysis=not isFlightDataValid(flightData[:10])
            )

            logging.info("Processing Complete Flight ID [%s]", self.flightID)
        except MySQLdb.Error, e:
            logging.exception("MySQLdb Error [%d]: %s", e.args[0], e.args[1])
            logging.exception("Last Executed Query: %s", cursor._last_executed)

        return -1
    # end def __call__()

# end class Task


def main(flightIDs, runWithMultiProcess, skipOutputToDB):
    '''
    Main function gets a list of all the files contained within the passed in
        folder name. Then scans through each file one-by-one in order to pass it
        to the analyze data function to find approaches and landings.
    After the data is analyzed, it then calls makeGraph to create the graph image.
    @author: Wyatt Hedrick, Kelton Karboviak
    '''
    # If there are no flight_ids passed as command-line args,
    # fetch all flights that haven't been analyzed for approaches yet
    # Otherwise the ids passed into argv will only be analyzed
    if len(flightIDs) == 0:
        globalCursor.execute(fetchFlightIDsSQL)
        flights = globalCursor.fetchall()
        flightIDs = [flight['flight_id'] for flight in flights]

    loadAirportData()

    tasks = multiprocessing.JoinableQueue()

    # If running in parallel, create NUM_CPUS number of Consumers for
    #   processing tasks.
    # If running linearly, only create 1 Consumer for processing tasks.
    num_consumers = NUM_CPUS if runWithMultiProcess else 1
    consumers = []
    for i in xrange(num_consumers):
        c = Consumer(tasks, skipOutputToDB)
        c.start()
        consumers.append(c)

    # Push all the flight IDs onto the tasks Queue for processing
    for flightID in flightIDs:
        tasks.put(Task(flightID))

    # Push None's onto Queue to signal to Consumers to stop consuming
    for i in xrange(num_consumers):
        tasks.put(None)

    # Cause main thread to wait for queue to be empty
    tasks.join()
# end def main()


def loadAirportData():
    '''
    Populate a dictionary containing airport data for all airports throughout the U.S.
    @author: Wyatt Hedrick
    '''
    with open('../data/Airports.csv', 'r') as infile:
        infile.readline()  # Trash line of data headers
        for line in infile:
            row = line.split(',')
            #             code,   name,   city,  state,      latitude,     longitude,      altitude
            a = Airport(row[0], row[1], row[2], row[3], float(row[4]), float(row[5]), float(row[6]))
            airports[row[0]] = a  # Insert into airports dict with airportCode as key

    with open('../data/AirportsDetailed.csv', 'r') as infile:
        infile.readline()  # Trash line of data headers
        for line in infile:
            row = line.split(',')
            #     airportCode,      altitude, runwayCode,      magHdg,        trueHdg,      centerLat,      centerLon
            r = Runway(row[2], float(row[6]), row[10], float(row[11]), float(row[12]), float(row[25]), float(row[26]))
            airports[row[2]].addRunway(r)  # Add runway to corresponding airport
# end def loadAirportData()


def isFlightDataValid(data):
    for value in data:
        if value['latitude'] not in (0, None) or value['longitude'] not in (0, None):
            return True
    return False
# end def isFlightDataValid()


@contextlib.contextmanager
def stopwatch(msg):
    """ Context manager to print how long a block of code ran. """
    t0 = time.time()
    try:
        yield
    finally:
        t1 = time.time()
    logger.info("Total elapsed time for %s: %.3f seconds", msg, t1 - t0)
# end def stopwatch()


'''
This checks to see if the program is being run directly via command-line. If it is, then it calls
    the main function passing in the command-line arguments
    # TODO Implement a command-line flag to have the program profile this program's run-time stats
'''
if __name__ == "__main__":
    # Parse command-line args
    parser = argparse.ArgumentParser(description='Tool to detect approaches in flight data.')
    parser.add_argument('flight_ids', metavar='flight_id', type=str, nargs='*', help='a flight_id to be analyzed')
    parser.add_argument('-m', '--multi-process', action='store_true', help='run program with multiple processes')
    parser.add_argument('--no-write', action='store_true', help='program will not write results to DB')
    args = parser.parse_args()

    try:
        globalConn = MySQLdb.connect(**db_config.credentials)
        globalCursor = globalConn.cursor(MySQLdb.cursors.DictCursor)

        with stopwatch("Program Execution"):
            main(args.flight_ids, args.multi_process, args.no_write)
    except MySQLdb.Error, e:
        print "MySQLdb Error [%d]: %s\n" % (e.args[0], e.args[1])
    finally:
        if globalConn is not None:
            globalConn.close()
