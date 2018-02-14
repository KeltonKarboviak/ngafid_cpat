# -*- coding: utf-8 -*-

from numpy import nan

from latlon import LatLon


class Airport(object):

    def __init__(
        self,
        code: str,
        name: str,
        city: str,
        state: str,
        lat: float,
        lon: float,
        alt: float
    ):
        self.code = code
        self.name = name
        self.city = city
        self.state = state
        self.centerLatLon = LatLon(float(lat), float(lon))
        self.alt = alt
        self.runways = []

    def __str__(self) -> str:
        return (
            '<Airport(code="{self.code}", name="{self.name}", '
            'city="{self.name}", state="{self.state}", '
            'center={self.centerLatLon}, altitude={self.alt})>'.format(
                self=self
            )
        )

    def __repr__(self):
        return str(self)

    def add_runway(self, runway):
        self.runways.append(runway)


class NullAirport(Airport):

    def __init__(self):
        super(NullAirport, self).__init__('', '', '', '', nan, nan, nan)
