#!/usr/bin/env python

import argparse
import config.db_config as db_config
import contextlib
import logging
import multiprocessing
import MySQLdb as mysql
import time
from Airport import Airport
from FlightAnalysis import FlightAnalyzer
from LatLon import LatLon
from Runway import Runway


""" LOGGING SETUP """
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(process)d - %(message)s")
logger = logging.getLogger(__name__)

""" IMPORT ENVIRONMENT-SPECIFIC CONFIGS """
ENV = "dev"
db_creds = db_config.credentials[ENV]

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
        self.conn = mysql.connect(**db_creds)
        self.cursor = self.conn.cursor(mysql.cursors.DictCursor)
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

        cursor = connection.cursor(mysql.cursors.DictCursor)

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
                skipAnalysis=False  # not isFlightDataValid(flightData[:10])
            )

            logging.info("Processing Complete Flight ID [%s]", self.flightID)
        except mysql.Error, e:
            logging.exception("MySQL Error [%d]: %s", e.args[0], e.args[1])
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
        # flightIDs = [392706, 393230, 382486, 387607, 393246, 388639, 382496, 393769, 387627, 389165, 395316, 383544, 389178, 387765, 383556, 393289, 382538, 394766, 387160, 388186, 388192, 390247, 386666, 387181, 395374, 394355, 381046, 392824, 394362, 394365, 387201, 392836, 384647, 392334, 393837, 385690, 384674, 394927, 388638, 392886, 392898, 386765, 389844, 389850, 382172, 382178, 384307, 394475, 386800, 383219, 394998, 392955, 388354, 383749, 384269, 384270, 382741, 381218, 383781, 385836, 389421, 383790, 381233, 385331, 392504, 384326, 395599, 393554, 393046, 392538, 387949, 394933, 381812, 394127, 389521, 388498, 394645, 384412, 390048, 389027, 384420, 381349, 383403, 386486, 393655, 384441, 384445, 390082, 384965, 384460, 382928, 395219, 395220, 390052, 384476, 385645, 397800, 397803, 390131, 385012]

    logging.info('Number of Flights to Analyze: %4d', len(flightIDs))

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
    """
    Populate a dictionary containing airport data for all airports throughout the U.S.
    @author: Wyatt Hedrick
    """
    with open('data/Airports.csv', 'r') as infile:
        infile.readline()  # Trash line of data headers
        for line in infile:
            row = line.split(',')
            #             code,   name,   city,  state,      latitude,     longitude,      altitude
            a = Airport(row[0], row[1], row[2], row[3], float(row[4]), float(row[5]), float(row[6]))
            airports[row[0]] = a  # Insert into airports dict with airportCode as key

    with open('data/AirportsDetailed.csv', 'r') as infile:
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
        globalConn = mysql.connect(**db_creds)
        globalCursor = globalConn.cursor(mysql.cursors.DictCursor)

        with stopwatch("Program Execution"):
            main(args.flight_ids, args.multi_process, args.no_write)
    except mysql.Error, e:
        print "MySQL Error [%d]: %s\n" % (e.args[0], e.args[1])
    finally:
        if globalConn is not None:
            globalConn.close()
