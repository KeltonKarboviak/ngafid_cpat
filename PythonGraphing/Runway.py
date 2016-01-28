class Runway:
    airport_code, runway_code = '', ''
    alt, heading, centerLat, centerLon = 0.0, 0.0, 0.0, 0.0

    def __init__(self, airport_code, alt, runway_code, heading, centerLat, centerLon):
        self.airport_code = airport_code
        self.alt = alt
        self.runway_code = runway_code
        self.heading = heading
        self.centerLat = centerLat
        self.centerLon = centerLon