<pre>

<?php
#import os
#import sys
#import time
#import datetime
require 'FlightAnalysis.php';
require 'FlightGraphing.php';
require 'LatLon.php';
require 'Airport.php';
require 'Runway.php';

$parameters = array(
    0  => array("param"=>"time",                  "data" => array(), "index" => -1, "label" => "Time",                  "units" => "minutes"),
    1  => array("param"=>"msl_altitude",          "data" => array(), "index" => -1, "label" => "Altitude",              "units" => "ft"),
    2  => array("param"=>"indicated_airspeed",    "data" => array(), "index" => -1, "label" => "Airspeed",              "units" => "kts"),
    3  => array("param"=>"vertical_airspeed",     "data" => array(), "index" => -1, "label" => "Vertical Airspeed",     "units" => "kts"),
    4  => array("param"=>"heading",               "data" => array(), "index" => -1, "label" => "Heading",               "units" => "degrees"),
    5  => array("param"=>"pitch_attitude",        "data" => array(), "index" => -1, "label" => "Pitch Attitude",        "units" => "degrees"),
    6  => array("param"=>"roll_attitude",         "data" => array(), "index" => -1, "label" => "Roll Attitude",         "units" => "degrees"),
    7  => array("param"=>"eng_1_rpm",             "data" => array(), "index" => -1, "label" => "Engine RPM",            "units" => "rpm"),
    8  => array("param"=>"vertical_acceleration", "data" => array(), "index" => -1, "label" => "Vertical Acceleration", "units" => "ft/s^2"),
    9  => array("param"=>"groundspeed",           "data" => array(), "index" => -1, "label" => "Groundspeed",           "units" => "kts"),
    10 => array("param"=>"latitude",              "data" => array(), "index" => -1, "label" => "Latitude",              "units" => "degrees"),
    11 => array("param"=>"longitude",             "data" => array(), "index" => -1, "label" => "Longitude",             "units" => "degrees"),
    12 => array("param"=>"LatLon",                "data" => array(), "index" => -1, "label" => "LatLon",                "units" => "degrees")
)

$airports = array();

'''
Populate a dictionary containing airport data for all airports throughout the U.S.
@author: Wyatt Hedrick
'''
function getAirportData()
{
    $airportFile = fopen("../data/Airports.csv", "r") or die("Unable to open file!");
    fgets($airportFile); #Trash line of headers
    while(!feof($airportFile))
    {
        $line = fgets($airportFile);
        $row = explode(",", $line);
        #             code,   name,   city,  state,      latitude,     longitude,      altitude
        $a = Airport($row[0], $row[1], $row[2], $row[3], (float)$row[4], (float)$row[5], (float)$row[6]);
        $airports[$row[0]] = $a;
    }

    $airportDetailed = fopen("../data/AirportsDetailed.csv", "r") or die("unable to open file!");
    fgets($airportDetailed); #Trash line of headers
    while(!feof($airportDetailed))
    {
        $line = fgets($airportDetailed);
        $row = explode(",", $line);
        #        airportCode,      altitude,  runwayCode,       magHdg,         trueHdg,       centerLat,       centerLon
        $r = Runway($row[2], (float)$row[6], $row[10], (float)$row[11], (float)$row[12], (float)$row[25], (float)$row[26]);
        $airports[$row[2]].addRunway($r);
    }

}

'''
Function clears the contents of each sub-list in the passed in list.
It does not delete the sub-lists themselves.
For example, after this function: data = [ [], [], ... ]
This happens by reference so data does not need to be returned.
@author: Kelton Karboviak
'''
function clearData()
{
    $parameters = array_fill_keys(array_keys($parameters), NULL);
}

'''
Main function gets a list of all the files contained within the passed in
    folder name. Then scans through each file one-by-one in order to pass it
    to the analyze data function to find approaches and landings.
After the data is analyzed, it then calls makeGraph to create the graph image.
@author: Wyatt Hedrick, Kelton Karboviak
'''
function main()
{

}

main();

?>

</pre>
