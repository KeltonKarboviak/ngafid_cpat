<?php
/* - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  *
 *  Vector-based spherical geodetic (latitude/longitude) functions    (c) Chris Veness 2011-2016  *
 *                                                                                   MIT Licence  *
 * www.movable-type.co.uk/scripts/latlong-vectors.html                                            *
 * www.movable-type.co.uk/scripts/geodesy/docs/module-latlon-nvector-spherical.html               *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  */

require 'Vector3d.php';


/**
 * Tools for working with points and paths on (a spherical model of) the earth’s surface using a
 * vector-based approach using 'n-vectors' (rather than the more common spherical trigonometry:
 * a vector-based approach makes many calculations much simpler, and easier to follow, compared
 * with trigonometric equivalents).
 *
 * Note on a spherical model earth, an n-vector is equivalent to a normalized version of an (ECEF)
 * cartesian coordinate.
 *
 * @module   latlon-vectors
 * @requires Vector3d
 */
class LatLon
{
    //Instance Variables
    private $lat = 0.0;
    private $lon = 0.0;

    /**
     * Creates a LatLon point on spherical model earth.
     *
     * @constructor
     * @param {number} lat - Latitude in degrees.
     * @param {number} lon - Longitude in degrees.
     *
     * @example
     *   var p1 = new LatLon(52.205, 0.119);
     */
    function LatLon($lat, $lon)
    {
        $this->lat = $lat;
        $this->lon = $lon;
    }


    /**
     * Converts ‘this’ lat/lon point to Vector3d n-vector (normal to earth's surface).
     *
     * @returns {Vector3d} Normalized n-vector representing lat/lon point.
     *
     * @example
     *   var p = new LatLon(45, 45);
     *   var v = p->toVector(); // [0.5000,0.5000,0.7071]
     */
    function toVector()
    {
        $rLat = deg2rad($this->lat);
        $rLon = deg2rad($this->lon);

        $x = cos($rLat) * cos($rLon);
        $y = cos($rLat) * sin($rLon);
        $z = sin($rLat);

        return new Vector3d($x, $y, $z);
    }


    /**
     * N-vector normal to great circle obtained by heading on given bearing from ‘this’ point.
     *
     * Direction of vector is such that initial bearing vector b = c × p.
     *
     * @param   {number}   bearing - Compass bearing in degrees.
     * @returns {Vector3d} Normalized vector representing great circle.
     *
     * @example
     *   var p1 = new LatLon(53.3206, -1.7297);
     *   var gc = p1->greatCircle(96.0); // [-0.794,0.129,0.594]
     */
    function greatCircle($bearing)
    {
        $rLat = deg2rad($this->lat);
        $rLon = deg2rad($this->lon);
        $theta = deg2rad($bearing);

        $x =  sin($rLon) * cos($theta) - sin($rLat) * cos($rLon) * sin($theta);
        $y = -cos($rLon) * cos($theta) - sin($rLat) * sin($rLon) * sin($theta);
        $z =  cos($rLat) * sin($theta);

        return new Vector3d($x, $y, $z);
    }


    /**
     * Returns the distance from ‘this’ point to the specified point.
     *
     * @param   {LatLon} point - Latitude/longitude of destination point.
     * @param   {number} [radius=6371e3] - (Mean) radius of earth (defaults to radius in meters).
     * @returns {number} Distance between this point and destination point, in same units as radius.
     *
     * @example
     *   var p1 = new LatLon(52.205, 0.119);
     *   var p2 = new LatLon(48.857, 2.351);
     *   var d = p1->distanceTo(p2); // 404.3 km
     */
    function distanceTo($point, $radius=NULL)
    {
        if ($radius === NULL)  $radius = 6371000;

        $p1 = $this->toVector();
        $p2 = $point->toVector();

        $delta = $p1->angleTo($p2);
        $d = $delta * $radius;

        return d;
    }


    /**
     * Returns the (initial) bearing from ‘this’ point to the specified point, in compass degrees.
     *
     * @param   {LatLon} point - Latitude/longitude of destination point.
     * @returns {number} Initial bearing in degrees from North (0°..360°).
     *
     * @example
     *   var p1 = new LatLon(52.205, 0.119);
     *   var p2 = new LatLon(48.857, 2.351);
     *   var b1 = p1->bearingTo(p2); // 156.2°
     */
    function bearingTo($point)
    {
        $p1 = $this->toVector();
        $p2 = $point->toVector();

        $northPole = new Vector3d(0.0, 0.0, 1.0);

        $c1 = $p1->cross($p2);        // great circle through p1 & p2
        $c2 = $p1->cross($northPole); // great circle through p1 & north pole

        // bearing is (signed) angle between c1 & c2
        $bearing = rad2deg( $c1->angleTo($c2, $p1) );

        return ($bearing + 360) % 360; // normalize to [0, 360]
    }


    /**
     * Returns the midpoint between ‘this’ point and specified point.
     *
     * @param   {LatLon} point - Latitude/longitude of destination point.
     * @returns {LatLon} Midpoint between this point and destination point.
     *
     * @example
     *   var p1 = new LatLon(52.205, 0.119);
     *   var p2 = new LatLon(48.857, 2.351);
     *   var pMid = p1->midpointTo(p2); // 50.5363°N, 001.2746°E
     */
    function midpointTo($point)
    {
        $p1 = $this->toVector();
        $p2 = $point->toVector();

        $mid = $p1->plus($p2)->unit();

        return $mid->toLatLonS();
    }


    /**
     * Returns the destination point from ‘this’ point having travelled the given distance on the
     * given initial bearing (bearing will normally vary before destination is reached).
     *
     * @param   {number} distance - Distance travelled, in same units as earth radius (default: meters).
     * @param   {number} bearing - Initial bearing in degrees from north.
     * @param   {number} [radius=6371e3] - (Mean) radius of earth (defaults to radius in meters).
     * @returns {LatLon} Destination point.
     *
     * @example
     *   var p1 = new LatLon(51.4778, -0.0015);
     *   var p2 = p1->destinationPoint(7794, 300.7); // 51.5135°N, 000.0983°W
     */
    function destinationPoint($distance, $bearing, $radius=NULL)
    {
        if ($radius === NULL)  $radius = 6371000;

        $delta = $distance / $radius; // angular distance in radians

        // get great circle obtained by starting from 'this' point on given bearing
        $c = $this->greatCircle($bearing);

        $p1 = $this->toVector();

        $x = $p1->times(cos($delta));           // component of p2 parallel to p1
        $y = $c->cross(p1)->times(sin($delta)); // component of p2 perpendicular to p1

        $p2 = $x->plus($y)->unit();

        return $p2->toLatLonS();
    }


    /**
     * Returns (signed) distance from ‘this’ point to great circle defined by start-point and end-point/bearing.
     *
     * @param   {LatLon}        pathStart - Start point of great circle path.
     * @param   {LatLon|number} pathBrngEnd - End point of great circle path or initial bearing from great circle start point.
     * @param   {number}        [radius=6371e3] - (Mean) radius of earth (defaults to radius in meters).
     * @returns {number}        Distance to great circle (-ve if to left, +ve if to right of path).
     *
     * @example
     *   var pCurrent = new LatLon(53.2611, -0.7972);
     *
     *   var p1 = new LatLon(53.3206, -1.7297), brng = 96.0;
     *   var d = pCurrent->crossTrackDistanceTo(p1, brng);// -305.7 m
     *
     *   var p1 = new LatLon(53.3206, -1.7297), p2 = new LatLon(53.1887, 0.1334);
     *   var d = pCurrent->crossTrackDistanceTo(p1, p2);  // -307.5 m
     */
    function crossTrackDistanceTo($pathStart, $pathBrngEnd, $radius=NULL)
    {
        if ($radius === NULL)  $radius = 6371000;

        $p = $this->toVector();

        if ( isinstance(pathBrngEnd, LatLon) )
            // great circle defined by two points
            $gc = $pathStart->toVector()->cross($pathBrngEnd->toVector());
        else
            // great circle defined by point + bearing
            $gc = $pathStart->greatCircle($pathBrngEnd);

        // (signed) angle between point & great circle normal vector
        $alpha = $gc->angleTo($p, $p->cross($gc)); 
        $alpha = ($alpha < 0 ? -M_PI : M_PI) / 2 - $alpha;

        $d = $alpha * $radius;

        return $d;
    }


    /**
     * String representation of LatLon point.
     *
     * @param   {number} [precision=5] - Number of decimal places to be used.
     * @returns {string} LatLon represented as (lat, lon).
     */
    function __toString()
    {
        return "({$this->lat}, {$this->lon})";
    }
}


/**
 * Converts ‘this’ (geocentric) cartesian vector to (spherical) latitude/longitude point.
 *
 * @returns  {LatLon} Latitude/longitude point vector points to.
 *
 * @example
 *   var v = new Vector3d(0.500, 0.500, 0.707);
 *   var p = v->toLatLonS(); // 45.0°N, 45.0°E
 */
function toLatLonS()
{
    $rLat = atan2($this->z, sqrt($this->x*$this->x + $this->y*$this->y));
    $rLon = atan2($this->y, $this->x);
    return new LatLon(rad2deg($rLat), rad2deg($rLon));
}

// Assign toLatLonS function prototype to Vector3d class
//Vector3d->toLatLonS = toLatLonS;
?>