class Airport:
    code, name, city, state = '', '', '', ''
    lat, lon, alt = 0.0, 0.0, 0.0
    runways = []

    def __init__(self, code, name, city, state, lat, lon, alt):
        self.code = code
        self.name = name
        self.city = city
        self.state = state
        self.lat = lat
        self.lon = lon
        self.alt = alt
        self.runways = []

    def addRunway(self, runway):
        self.runways.append(runway)