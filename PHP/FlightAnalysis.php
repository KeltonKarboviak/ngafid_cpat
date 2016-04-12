<?php

require 'LatLon.php';
require 'Vector3d.php';
#import os
#import math


define("EARTH_RADIUS_MILES", 3959);
define("EARTH_RADIUS_FEET", 20900000);
define("APPROACH_MIN_IAS", 55);
define("APPROACH_MAX_IAS", 75);
define("APPROACH_MAX_HEADING_ERROR", 10);
define("APPROACH_MIN_VAS", -1000);
define("APPROACH_MAX_CROSSTRACK_ERROR", 50)
define("APPROACH_MIN_DISTANCE", 1);
define("APPROACH_MIN_ALTITUDE_AGL", 500);
define("APPROACH_FINAL_MAX_ALTITUDE_AGL", 150);
define("APPROACH_FINAL_MIN_ALTITUDE_AGL", 50);
define("FULL_STOP_SPEED_INDICATOR", 35);
define("TOUCH_AND_GO_ELEVATION_INDICATOR", 5);
define("RUNWAY_SELECTION_INDICATOR", 20);

class FlightAnalysis
{
    private $parameters = array();
    private $airports = array();
    private $approaches = array();
    private $approachID = 0;
    private $timestamp = "";
    private $folder = "";
    private $flightID = "";

    function FlightAnalysis($time, $folder, $a)
    {
        $this->timestamp = $time;
        $this->folder = $folder;
        $this->airports = $a;
    }

    function analyze($flightID, $p)
    {

    }

    '''
    Function clears the contents of the approaches dictionary
    @author: Kelton Karboviak
    '''
    function clearApproaches()
    {

    }

    '''
    This function will reset the approachID to 0 on the start of a new flight.
    @author Wyatt Hedrick, Kelton Karboviak
    '''
    function resetApproachID()
    {

    }

    '''
    This function will return a unique approachID for each approach in the flight.
    @returns aID the unique approachID associated with the approach.
    @author Wyatt Hedrick, Kelton Karboviak
    '''
    function getApproachID()
    {

    }

    '''
    This function will find the initial takeoff and return the first time value after the initial takeoff
    @return the first time index after the initial takeoff
    '''
    function findInitialTakeOff()
    {

    }

    '''
    This function analyzes the flight data.
    So far we have implemented a check for full stops.
    @param startingIndex the time index after the initial takeoff
    @author: Wyatt Hedrick, Kelton Karboviak
    '''
    function analyzeApproaches($startingIndex)
    {

    }

    '''
    This function will analyze the time after the final approach and before the plane reaches a height of 150 feet (or until the flight ends if it is the final landing).
    @param: start the time index when the approach ends and the landing begins.
    @param: airport the airport that the airplane is attempting to land at
    @author: Wyatt Hedrick
    '''
    function analyzeLanding($start, $airport, $thisApproachID)
    {

    }

    '''
    This function calculates the distance the airplane is from the center line in feet based on the passed in coordinates of the airplane and the runway the plane is attempting to land at.

    GIS Mapping Tool for verification: http://gistools.igismap.com/bearing

    @param: airplaneLat the latitude of the airplane
    @param: airplaneLon the longitude of the airplane
    @param: runway the runway object representing the closest runway to the airplane
    @returns: the distance in feet between the airplane and the center line of the runway
    @author: Wyatt Hedrick, Kelton Karboviak
    '''
    function crossTrackToCenterLine($airplanePoint, $runway)
    {

    }

    '''
    This function detects the airport that is closest to the passed in coordinates.
    It performs this by scanning the airportData dictionary and calculating which
        airport as the lowest total difference between lat/lon.
    @param: lat the latitude of the plane
    @param: lon the longitude of the plane
    @author: Wyatt Hedrick
    '''
    function detectAirport($airplanePoint)
    {

    }

    '''
    This function will detect the runway that the airplane is going to attempt to land at.
    @param: airplaneLat the latitude of the airplane
    @param: airplaneLon the longitude of the airplane
    @param: airplaneHdg the heading of the heading
    @param: airport the airport object that represents the closest airport to the airplane
    @returns: the runway object representing the runway the airplane is attempting to land on
    @author: Wyatt Hedrick, Kelton Karboviak
    '''
    function detectRunway($airplanePoint, $airplaneHdg, $airport)
    {

    }

    '''
    Outputs the approach analysis information to a .csv file. The file will be saved to
        ./results/results_flightID.csv, and appended to ./results/query_timestamp.csv
    @param flightID string of the current flight ID to write to a CSV file
    @param timestamp string of the timestamp when the program started running.
        This will be used as the filename to store the results of all flights for this program run
    @param folder string of the folder in which to store the result CSV file
    @author: Kelton Karboviak
    '''
    function outputToCSV()
    {

    }


}

?>
