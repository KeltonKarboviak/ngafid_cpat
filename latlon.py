# -*- coding: utf-8 -*-

"""
Vector-based spherical geodetic (latitude/longitude) functions
(c) Chris Veness 2011-2016 MIT License

www.movable-type.co.uk/scripts/latlong-vectors.html
www.movable-type.co.uk/scripts/geodesy/docs/module-latlon-nvector-spherical.html
"""

import math
from typing import Union

from vector3d import Vector3d


class LatLon(object):
    """
    Tools for working with points and paths on (a spherical model of) the
    earth’s surface using a vector-based approach using 'n-vectors' (rather
    than the more common spherical trigonometry: a vector-based approach makes
    many calculations much simpler, and easier to follow, compared with
    trigonometric equivalents).

    Note on a spherical model earth, an n-vector is equivalent to a normalized
    version of an (ECEF) * cartesian coordinate.
    """

    def __init__(self, lat: float, lon: float):
        """
        Creates a LatLon point on spherical model earth.
        :param lat: float Latitude in degrees.
        :param lon: float Longitude in degrees.

        >>> p1 = LatLon(52.205, 0.119)
        """
        self.lat = float(lat)
        self.lon = float(lon)

    def __str__(self) -> str:
        """
        String representation of LatLon point.
        :rtype: str
        :return: LatLon represented as (lat, lon).
        """
        return "({self.lat:5f}, {self.lon:5f})".format(self=self)

    def __repr__(self):
        return "<LatLon(lat={self.lat:5f}, lon={self.lon:5f})".format(self=self)

    def to_vector(self) -> Vector3d:
        """
        Converts 'self' to Vector3d n-vector (normal to earth's surface).
        :rtype: Vector3d
        :return: Normalized n-vector representing lat/lon point.

        >>> p = LatLon(45, 45)
        >>> p.to_vector()
        <Vector3d(x=0.500000, 0.500000, 0.707107)>
        """
        r_lat = math.radians(self.lat)
        r_lon = math.radians(self.lon)

        x = math.cos(r_lat) * math.cos(r_lon)
        y = math.cos(r_lat) * math.sin(r_lon)
        z = math.sin(r_lat)

        return Vector3d(x, y, z)

    def great_circle(self, bearing: float) -> Vector3d:
        """
        N-vector normal to great circle obtained by heading on given bearing
        from 'self'.
        :param bearing: Compass bearing in degrees.
        :rtype: Vector3d
        :return: Normalized vector representing great circle.

        >>> p1 = LatLon(53.3206, -1.7297)
        >>> p1.great_circle(96.0)
        <Vector3d(x=-0.794079, 0.128556, 0.594065)>
        """
        r_lat = math.radians(self.lat)
        r_lon = math.radians(self.lon)
        theta = math.radians(bearing)

        x = math.sin(r_lon) * math.cos(theta) \
            - math.sin(r_lat) * math.cos(r_lon) * math.sin(theta)
        y = -math.cos(r_lon) * math.cos(theta) \
            - math.sin(r_lat) * math.sin(r_lon) * math.sin(theta)
        z = math.cos(r_lat) * math.sin(theta)

        return Vector3d(x, y, z)

    def distance_to(self, point: 'LatLon', radius: int = 6371e3) -> float:
        """
        Returns the distance from 'self' to the specified point.
        :param point: Latitude/longitude of destination point.
        :param radius: (Mean) radius of earth (defaults to radius in meters).
        :rtype: float
        :return: Distance between this point and destination point, in same
        units as radius.

        >>> p1 = LatLon(52.205, 0.119)
        >>> p2 = LatLon(48.857, 2.351)
        >>> p1.distance_to(p2)
        404279.16398867936
        """
        p1 = self.to_vector()
        p2 = point.to_vector()

        delta = p1.angleTo(p2)
        d = delta * radius

        return d

    def bearing_to(self, point: 'LatLon') -> float:
        """
        Returns the (initial) bearing from 'self'to the specified point, in
        compass degrees.
        :param point: Latitude/longitude of destination point.
        :rtype: float
        :return: Initial bearing in degrees from North (0°..360°).

        >>> p1 = LatLon(52.205, 0.119)
        >>> p2 = LatLon(48.857, 2.351)
        >>> p1.bearing_to(p2)
        156.16658258153177
        """
        p1 = self.to_vector()
        p2 = point.to_vector()

        north_pole = Vector3d(0.0, 0.0, 1.0)

        c1 = p1.cross(p2)  # great circle through p1 & p2
        c2 = p1.cross(north_pole)  # great circle through p1 & north pole

        # bearing is (signed) angle between c1 & c2
        bearing = math.degrees(c1.angleTo(c2, p1))

        return (bearing + 360) % 360  # normalize to [0, 360]

    def midpoint_to(self, point: 'LatLon') -> 'LatLon':
        """
        Returns the midpoint between 'self' and specified point.
        :param point: Latitude/longitude of destination point.
        :rtype: LatLon
        :return: Midpoint between 'self' point and destination point.

        >>> p1 = LatLon(52.205, 0.119)
        >>> p2 = LatLon(48.857, 2.351)
        >>> p1.midpoint_to(p2)
        <LatLon(lat=50.536327, lon=1.274614)
        """
        p1 = self.to_vector()
        p2 = point.to_vector()

        mid = p1.plus(p2).unit()

        return mid.toLatLonS()

    def destination_point(
        self,
        distance: float,
        bearing: float,
        radius: int = 6371e3
    ) -> 'LatLon':
        """
        Returns the destination point from 'self' having traveled the given
        distance on the given initial bearing (bearing will normally vary
        before destination is reached).
        :param distance: Distance traveled, in same units as earth radius
        (default: meters).
        :param bearing: Initial bearing in degrees from north.
        :param radius: (Mean) radius of earth (defaults to radius in meters).
        :rtype: LatLon
        :return: Destination point.

        >>> p1 = LatLon(51.4778, -0.0015)
        >>> p1.destination_point(7794, 300.7)
        <LatLon(lat=51.513546, lon=-0.098345)
        """
        delta = distance / radius  # angular distance in radians

        # get great circle obtained by starting from 'self' on given bearing
        c = self.great_circle(bearing)

        p1 = self.to_vector()

        # component of p2 parallel to p1
        x = p1.times(math.cos(delta))

        # component of p2 perpendicular to p1
        y = c.cross(p1).times(math.sin(delta))

        p2 = x.plus(y).unit()

        return p2.toLatLonS()

    def cross_track_distance_to(
        self,
        path_start: 'LatLon',
        path_brng_end: Union['LatLon', float],
        radius: int = 6371e3
    ) -> float:
        """
        Returns (signed) distance from 'self' to great circle defined by
        start-point and end-point/bearing.
        :param path_start: Start point of great circle path.
        :param path_brng_end: End point of great circle path or initial bearing
        from great circle start point.
        :param radius: (Mean) radius of earth (defaults to radius in meters).
        :rtype: float
        :return: Distance to great circle (-ve if to left, +ve if to right of
        path).

        >>> pCurrent = LatLon(53.2611, -0.7972)
        >>> p1 = LatLon(53.3206, -1.7297)
        >>> brng = 96.0
        >>> pCurrent.cross_track_distance_to(p1, brng)
        -305.66486077528987

        >>> p1 = LatLon(53.3206, -1.7297)
        >>> p2 = LatLon(53.1887, 0.1334)
        >>> pCurrent.cross_track_distance_to(p1, p2)
        -307.54957041913156
        """
        p = self.to_vector()

        if isinstance(path_brng_end, LatLon):
            # great circle defined by two points
            gc = path_start.to_vector().cross(path_brng_end.to_vector())
        else:
            # great circle defined by point + bearing
            gc = path_start.great_circle(path_brng_end)

        # (signed) angle between point & great circle normal vector
        alpha = gc.angleTo(p, p.cross(gc))

        # (signed) angle between point & great circle
        alpha = (-1 if alpha < 0 else 1) * math.pi / 2 - alpha

        d = alpha * radius

        return d


def to_latlon(self) -> LatLon:
    """
    Converts 'self' (geocentric) cartesian vector to (spherical)
    latitude/longitude point.
    :rtype: LatLon
    :return: Latitude/longitude point vector points to.

    >>> v = Vector3d(0.500, 0.500, 0.707)
    >>> v.to_latlon()
    <LatLon(lat=44.995674, lon=45.000000)
    """
    r_lat = math.atan2(self.z, math.sqrt(self.x * self.x + self.y * self.y))
    r_lon = math.atan2(self.y, self.x)

    return LatLon(math.degrees(r_lat), math.degrees(r_lon))


# Assign to_latlon function prototype to Vector3d class
Vector3d.toLatLonS = to_latlon
