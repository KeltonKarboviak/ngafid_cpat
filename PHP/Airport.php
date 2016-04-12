<?php

require 'LatLon.php';

class Airport
{
        private $code = "";
        private $name = "";
        private $city = "";
        private $state = "";
        private $centerLatLon = NULL;
        private $alt = 0.0;
        private $runways = array();

        function Airport($code, $name, $city, $state, $lat, $lon, $alt)
        {
            $this->code = $code;
            $this->name = $name;
            $this->city = $city;
            $this->state = $state;
            $this->centerLatLon = LatLon($lat, $lon);
            $this->runways = array();
        }

        function addRunway($runway)
        {
            $this->runways.append($runway);
        }
}

 ?>
