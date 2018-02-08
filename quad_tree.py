#!/usr/bin/env python

from math import fabs


class QuadTree(object):
    MIN_GRID_SIZE = 0.025

    def __init__(self, lat_min=-180, lat_max=180, lon_min=-180, lon_max=180):
        self._lat_min, self._lat_mid, self._lat_max = lat_min, (lat_min + lat_max) / 2.0, lat_max
        self._lon_min, self._lon_mid, self._lon_max = lon_min, (lon_min + lon_max) / 2.0, lon_max

        self._nodes = {
            'northwest': None,
            'northeast': None,
            'southwest': None,
            'southeast': None,
        }
        # self._northwest, self._northeast, self._southwest, self._southeast = (None, None, None, None)

        self._airport = None

        lat_diff = fabs(lat_min - lat_max)
        lon_diff = fabs(lon_min - lon_max)

        # print('lat_diff:', lat_diff, ' lon_diff:', lon_diff)

        if fabs(lat_min - lat_max) < self.MIN_GRID_SIZE and fabs(lon_min - lon_max) < self.MIN_GRID_SIZE:
            self._is_leaf = True
        else:
            self._is_leaf = False

    def __str__(self):
        return (
            '<QuadTree(lat_min={self._lat_min}, lat_mid={self._lat_mid}, lat_max={self._lat_max}, '
            'lon_min={self._lon_min}, lon_mid={self._lon_mid}, lon_max={self._lon_max}, leaf={self._is_leaf})>'.format(self=self)
        )

    def __repr__(self):
        return str(self)

    def get_lat_direction(self, lat):
        if lat < self._lat_mid:
            # South
            return ('south', (self._lat_min, self._lat_mid))
        else:
            # North
            return ('north', (self._lat_mid, self._lat_max))

    def get_lon_direction(self, lon):
        if lon < self._lon_mid:
            # West
            return ('west', (self._lon_min, self._lon_mid))
        else:
            # East
            return ('east', (self._lon_mid, self._lon_max))

    def insert(self, airport):
        # print(self, end='\t')

        if self._is_leaf:
            self._airport = airport
        else:
            lat_dir = self.get_lat_direction(airport.centerLatLon.lat)
            lon_dir = self.get_lon_direction(airport.centerLatLon.lon)

            direction = lat_dir[0] + lon_dir[0]
            # print('Going', direction, (lat_dir[1], lon_dir[1]))

            # Check if node hasn't been created already
            if not self._nodes[direction]:
                self._nodes[direction] = QuadTree(*lat_dir[1], *lon_dir[1])

            self._nodes[direction].insert(airport)

            # if airport.centerLatLon.lat < self._lat_mid:
            #     # South
            #     direction += 'south'
            #     if airport.centerLatLon.lon < self._lon_mid:
            #         # West
            #         direction += 'west'
            #         print('southwest!')
            #         self._southwest = QuadTree(self._lat_min, self._lat_mid, self._lon_min, self._lon_mid)
            #         self._southwest.insert(airport)
            #     else:
            #         # East
            #         direction += 'east'
            #         print('southeast!')
            #         self._southeast = QuadTree(self._lat_min, self._lat_mid, self._lon_mid, self._lon_max)
            #         self._southeast.insert(airport)
            # else:
            #     # North
            #     direction += 'north'
            #     if airport.centerLatLon.lon < self._lon_mid:
            #         # West
            #         direction += 'west'
            #         print('northwest!')
            #         self._northwest = QuadTree(self._lat_mid, self._lat_max, self._lon_min, self._lon_max)
            #         self._northwest.insert(airport)
            #     else:
            #         # East
            #         direction += 'east'
            #         print('northeast!')
            #         self._northeast = QuadTree(self._lat_mid, self._lat_max, self._lon_mid, self._lon_max)
            #         self._northeast.insert(airport)

    def get_nearest_airport(self, lat, lon):
        # print(self, end='\t')
        if self._is_leaf:
            return self._airport

        lat_dir = self.get_lat_direction(lat)
        lon_dir = self.get_lon_direction(lon)

        direction = lat_dir[0] + lon_dir[0]
        # print('Going ', direction)

        try:
            airport = self._nodes[direction].get_nearest_airport(lat, lon)
        except AttributeError as e:
            # Did not find a corresponding node, so return None
            airport = None
        finally:
            return airport
