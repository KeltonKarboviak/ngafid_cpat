class Runway:
    airport_code, runway_code = '', ''
    heading, alt, centerLat, centerLon = 0.0, 0.0, 0.0, 0.0

    def __init__(self, airport_code, alt, runway_code, heading, nwLat, nwLon, neLat, neLon, swLat, swLon, seLat, seLon):
        self.airport_code = airport_code
        self.alt = alt
        self.runway_code = runway_code
        self.heading = heading
        self.centerLat = (nwLat + neLat + swLat + seLat) / 4
        self.centerLon = (nwLon + neLon + swLon + seLon) / 4