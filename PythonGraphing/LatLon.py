# coding: utf-8
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  #
#  Vector-based spherical geodetic (latitude/longitude) functions    (c) Chris Veness 2011-2016  #
#                                                                                   MIT Licence  #
# www.movable-type.co.uk/scripts/latlong-vectors.html                                            #
# www.movable-type.co.uk/scripts/geodesy/docs/module-latlon-nvector-spherical.html               #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  #

import math
from Vector3d import Vector3d


'''
 * Tools for working with points and paths on (a spherical model of) the earth’s surface using a
 * vector-based approach using 'n-vectors' (rather than the more common spherical trigonometry:
 * a vector-based approach makes many calculations much simpler, and easier to follow, compared
 * with trigonometric equivalents).
 *
 * Note on a spherical model earth, an n-vector is equivalent to a normalised version of an (ECEF)
 * cartesian coordinate.
 *
 * @module   latlon-vectors
 * @requires vector3d
'''
class LatLon:
    lat, lon = 0.0, 0.0


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
    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon


    def toVector(self):
        rLat = math.radians(self.lat)
        rLon = math.radians(self.lon)

        x = math.cos(rLat) * math.cos(rLon)
        y = math.cos(rLat) * math.sin(rLon)
        z = math.sin(rLat)

        return Vector3d(x, y, z)




'''
 * Converts ‘this’ (geocentric) cartesian vector to (spherical) latitude/longitude point.
 *
 * @returns  {LatLon} Latitude/longitude point vector points to.
 *
 * @example
 *   var v = new Vector3d(0.500, 0.500, 0.707);
 *   var p = v.toLatLonS(); // 45.0°N, 45.0°E
'''
def toLatLonS(self):
    rLat = math.atan2(self.z, math.sqrt(self.x*self.x + self.y*self.y))
    rLon = math.atan2(self.y, self.x)
    return LatLon(math.degrees(rLat), math.degrees(rLon))

Vector3d.toLatLonS = toLatLonS
