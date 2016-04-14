<?php

require 'LatLon.php';

class Airport
{
        public $code = "";
        public $name = "";
        public $city = "";
        public $state = "";
        public $centerLatLon = NULL;
        public $alt = 0.0;
        public $runways = array();

        function Airport($code, $name, $city, $state, $lat, $lon, $alt)
        {
            $this->code = $code;
            $this->name = $name;
            $this->city = $city;
            $this->state = $state;
            $this->centerLatLon = new LatLon($lat, $lon);
        }

        function addRunway($runway)
        {
            $this->runways.append($runway);
        }
}

?>