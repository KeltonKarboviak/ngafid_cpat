# coding: utf-8
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  #
#  Vector-based spherical geodetic (latitude/longitude) functions    (c) Chris Veness 2011-2016  #
#                                                                                   MIT Licence  #
# www.movable-type.co.uk/scripts/latlong-vectors.html                                            #
# www.movable-type.co.uk/scripts/geodesy/docs/module-latlon-nvector-spherical.html               #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  #

import math
from Vector3d import Vector3d


class LatLon(object):
    '''
     * Tools for working with points and paths on (a spherical model of) the earth’s surface using a
     * vector-based approach using 'n-vectors' (rather than the more common spherical trigonometry:
     * a vector-based approach makes many calculations much simpler, and easier to follow, compared
     * with trigonometric equivalents).
     *
     * Note on a spherical model earth, an n-vector is equivalent to a normalized version of an (ECEF)
     * cartesian coordinate.
     *
     * @module   latlon-vectors
     * @requires vector3d
    '''

    def __init__(self, lat, lon):
        '''
         * Creates a LatLon point on spherical model earth.
         *
         * @constructor
         * @param {number} lat - Latitude in degrees.
         * @param {number} lon - Longitude in degrees.
         *
         * @example
         *   var p1 = new LatLon(52.205, 0.119);
        '''
        self.lat = float(lat)
        self.lon = float(lon)

    def __str__(self):
        '''
         * String representation of LatLon point.
         *
         * @returns {string} LatLon represented as (lat, lon).
        '''
        return "({self.lat:5f}, {self.lon:5f})".format(self=self)

    def __repr__(self):
        return "<LatLon(lat={self.lat:5f}, lon={self.lon:5f})".format(self=self)

    def toVector(self):
        '''
         * Converts ‘this’ lat/lon point to Vector3d n-vector (normal to earth's surface).
         *
         * @returns {Vector3d} Normalized n-vector representing lat/lon point.
         *
         * @example
         *   var p = new LatLon(45, 45);
         *   var v = p.toVector(); // [0.5000,0.5000,0.7071]
        '''
        rLat = math.radians(self.lat)
        rLon = math.radians(self.lon)

        x = math.cos(rLat) * math.cos(rLon)
        y = math.cos(rLat) * math.sin(rLon)
        z = math.sin(rLat)

        return Vector3d(x, y, z)

    def greatCircle(self, bearing):
        '''
         * N-vector normal to great circle obtained by heading on given bearing from ‘this’ point.
         *
         * Direction of vector is such that initial bearing vector b = c × p.
         *
         * @param   {number}   bearing - Compass bearing in degrees.
         * @returns {Vector3d} Normalized vector representing great circle.
         *
         * @example
         *   var p1 = new LatLon(53.3206, -1.7297);
         *   var gc = p1.greatCircle(96.0); // [-0.794,0.129,0.594]
        '''
        rLat = math.radians(self.lat)
        rLon = math.radians(self.lon)
        theta = math.radians(bearing)

        x =  math.sin(rLon) * math.cos(theta) - math.sin(rLat) * math.cos(rLon) * math.sin(theta)
        y = -math.cos(rLon) * math.cos(theta) - math.sin(rLat) * math.sin(rLon) * math.sin(theta)
        z =  math.cos(rLat) * math.sin(theta)

        return Vector3d(x, y, z)

    def distanceTo(self, point, radius=None):
        '''
         * Returns the distance from ‘this’ point to the specified point.
         *
         * @param   {LatLon} point - Latitude/longitude of destination point.
         * @param   {number} [radius=6371e3] - (Mean) radius of earth (defaults to radius in meters).
         * @returns {number} Distance between this point and destination point, in same units as radius.
         *
         * @example
         *   var p1 = new LatLon(52.205, 0.119);
         *   var p2 = new LatLon(48.857, 2.351);
         *   var d = p1.distanceTo(p2); // 404.3 km
        '''
        radius = 6371000 if radius is None else radius

        p1 = self.toVector()
        p2 = point.toVector()

        delta = p1.angleTo(p2)
        d = delta * radius

        return d

    def bearingTo(self, point):
        '''
         * Returns the (initial) bearing from ‘this’ point to the specified point, in compass degrees.
         *
         * @param   {LatLon} point - Latitude/longitude of destination point.
         * @returns {number} Initial bearing in degrees from North (0°..360°).
         *
         * @example
         *   var p1 = new LatLon(52.205, 0.119);
         *   var p2 = new LatLon(48.857, 2.351);
         *   var b1 = p1.bearingTo(p2); // 156.2°
        '''
        p1 = self.toVector()
        p2 = point.toVector()

        northPole = Vector3d(0.0, 0.0, 1.0)

        c1 = p1.cross(p2)         # great circle through p1 & p2
        c2 = p1.cross(northPole)  # great circle through p1 & north pole

        # bearing is (signed) angle between c1 & c2
        bearing = math.degrees( c1.angleTo(c2, p1) )

        return (bearing + 360) % 360  # normalize to [0, 360]

    def midpointTo(self, point):
        '''
         * Returns the midpoint between ‘this’ point and specified point.
         *
         * @param   {LatLon} point - Latitude/longitude of destination point.
         * @returns {LatLon} Midpoint between this point and destination point.
         *
         * @example
         *   var p1 = new LatLon(52.205, 0.119);
         *   var p2 = new LatLon(48.857, 2.351);
         *   var pMid = p1.midpointTo(p2); // 50.5363°N, 001.2746°E
        '''
        p1 = self.toVector()
        p2 = point.toVector()

        mid = p1.plus(p2).unit()

        return mid.toLatLonS()

    def destinationPoint(self, distance, bearing, radius=None):
        '''
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
         *   var p2 = p1.destinationPoint(7794, 300.7); // 51.5135°N, 000.0983°W
        '''
        radius = 6371000 if radius is None else radius

        delta = distance / radius  # angular distance in radians

        # get great circle obtained by starting from 'this' point on given bearing
        c = self.greatCircle(bearing)

        p1 = self.toVector()

        x = p1.times(math.cos(delta))           # component of p2 parallel to p1
        y = c.cross(p1).times(math.sin(delta))  # component of p2 perpendicular to p1

        p2 = x.plus(y).unit()

        return p2.toLatLonS()

    def crossTrackDistanceTo(self, pathStart, pathBrngEnd, radius=None):
        '''
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
         *   var d = pCurrent.crossTrackDistanceTo(p1, brng);// -305.7 m
         *
         *   var p1 = new LatLon(53.3206, -1.7297), p2 = new LatLon(53.1887, 0.1334);
         *   var d = pCurrent.crossTrackDistanceTo(p1, p2);  // -307.5 m
        '''
        radius = 6371000 if radius is None else radius

        p = self.toVector()

        if isinstance(pathBrngEnd, LatLon):
            # great circle defined by two points
            gc = pathStart.toVector().cross(pathBrngEnd.toVector())
        else:
            # great circle defined by point + bearing
            gc = pathStart.greatCircle(pathBrngEnd)

        alpha = gc.angleTo(p, p.cross(gc))  # (signed) angle between point & great circle normal vector
        alpha = -math.pi / 2 - alpha if alpha < 0 else math.pi / 2 - alpha  # (signed) angle between point & great circle

        d = alpha * radius

        return d


def toLatLonS(self):
    '''
     * Converts ‘this’ (geocentric) cartesian vector to (spherical) latitude/longitude point.
     *
     * @returns  {LatLon} Latitude/longitude point vector points to.
     *
     * @example
     *   var v = new Vector3d(0.500, 0.500, 0.707);
     *   var p = v.toLatLonS(); // 45.0°N, 45.0°E
    '''
    rLat = math.atan2(self.z, math.sqrt(self.x*self.x + self.y*self.y))
    rLon = math.atan2(self.y, self.x)

    return LatLon(math.degrees(rLat), math.degrees(rLon))


# Assign toLatLonS function prototype to Vector3d class
Vector3d.toLatLonS = toLatLonS
