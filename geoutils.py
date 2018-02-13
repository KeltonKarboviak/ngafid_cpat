# -*- coding: utf-8 -*-

from math import pi

import numpy as np
from numpy import (
    absolute,
    arcsin as asin,
    arctan as atan,
    arctan2 as atan2,
    cos,
    degrees,
    radians,
    sin,
    sqrt,
    tan,
)


EQUATOR_RADIUS_MILES = 3963.1906
POLAR_RADIUS_MILES = 3949.90276423
MAJOR_AXIS_MILES = EQUATOR_RADIUS_MILES
MINOR_AXIS_MILES = POLAR_RADIUS_MILES
FLATTENING = 1 / 298.257223563
MILES_TO_FEET = 5280.0


def signed_heading_difference(initial, final):
    """Calculate the error from a given initial heading to a final heading. If
    the shortest distance from the initial heading to the final heading is by
    going around a compass clockwise, the result will be positive. Otherwise,
    the result will be negative.
    """
    if np.array(
        (initial > 360) | (initial < 0) | (final > 360) | (final < 0)
    ).any():
        raise ValueError('Inputs need to be within the following range: [0, 360]')

    diff = final - initial
    abs_diff = absolute(diff)

    return np.where(
        abs_diff <= 180,
        np.where(abs_diff == 180, abs_diff, diff),
        np.where(final > initial, abs_diff - 360, 360 - abs_diff)
    )


def unsigned_heading_difference(initial, final):
    """Calculate the error from a given initial heading to a final heading. The
    result will be the absolute value of the error.
    """
    if np.array(
        (initial > 360) | (initial < 0) | (final > 360) | (final < 0)
    ).any():
        raise ValueError('Inputs need to be within the following range: [0, 360]')

    return 180 - abs(abs(initial - final) - 180)


def vincenty_distance(lats1, lons1, lats2, lons2):
    """Vincenty inverse formula calculation.

    Reference: https://en.wikipedia.org/wiki/Vincenty%27s_formulae
    """
    major, minor, f = MAJOR_AXIS_MILES, MINOR_AXIS_MILES, FLATTENING

    lats1, lons1 = radians(lats1), radians(lons1)
    lats2, lons2 = radians(lats2), radians(lons2)

    delta_lons = lons2 - lons1

    reduced_lats1 = atan((1 - f) * tan(lats1))
    reduced_lats2 = atan((1 - f) * tan(lats2))

    sin_reduceds1, cos_reduceds1 = sin(reduced_lats1), cos(reduced_lats1)
    sin_reduceds2, cos_reduceds2 = sin(reduced_lats2), cos(reduced_lats2)

    lambda_lons = delta_lons
    lambda_primes = np.full_like(lambda_lons, fill_value=2 * pi, dtype='float64')

    iter_limit = 1000

    i = 0
    while (absolute(lambda_lons - lambda_primes) > 10e-12).any() and i <= iter_limit:
        i += 1

        sin_lambda_lons, cos_lambda_lons = sin(lambda_lons), cos(lambda_lons)

        sin_sigmas = sqrt(
            (cos_reduceds2 * sin_lambda_lons) ** 2 +
            (cos_reduceds1 * sin_reduceds2 -
                sin_reduceds1 * cos_reduceds2 * cos_lambda_lons) ** 2
        )

        # if sin_sigmas == 0:
        #     return 0 # Coincident points

        cos_sigmas = (
            sin_reduceds1 * sin_reduceds2 +
            cos_reduceds1 * cos_reduceds2 * cos_lambda_lons
        )

        sigmas = atan2(sin_sigmas, cos_sigmas)

        sin_alphas = (
            cos_reduceds1 * cos_reduceds2 * sin_lambda_lons / sin_sigmas
        )
        cos_sq_alphas = 1 - sin_alphas ** 2

        cos2_sigma_ms = np.where(
            cos_sq_alphas != 0,
            cos_sigmas - 2 * (sin_reduceds1 * sin_reduceds2 / cos_sq_alphas),
            0.0  # Equatorial line
        )

        C = f / 16. * cos_sq_alphas * (4 + f * (4 - 3 * cos_sq_alphas))

        lambda_primes = lambda_lons
        lambda_lons = (
            delta_lons + (1 - C) * f * sin_alphas * (
                sigmas + C * sin_sigmas * (
                    cos2_sigma_ms + C * cos_sigmas * (
                        -1 + 2 * cos2_sigma_ms ** 2
                    )
                )
            )
        )

    if i > iter_limit:
        raise ValueError("Vincenty formula failed to converge!")

    us_sq = cos_sq_alphas * (major ** 2 - minor ** 2) / minor ** 2

    A = 1 + us_sq / 16384. * (
        4096 + us_sq * (-768 + us_sq * (320 - 175 * us_sq))
    )

    B = us_sq / 1024. * (256 + us_sq * (-128 + us_sq * (74 - 47 * us_sq)))

    delta_sigmas = (
        B * sin_sigmas * (
            cos2_sigma_ms + B / 4. * (
                cos_sigmas * (
                    -1 + 2 * cos2_sigma_ms ** 2
                ) - B / 6. * cos2_sigma_ms * (
                    -3 + 4 * sin_sigmas ** 2
                ) * (
                    -3 + 4 * cos2_sigma_ms ** 2
                )
            )
        )
    )

    s = minor * A * (sigmas - delta_sigmas)

    return s


def bearing(start_lat, start_lon, end_lat, end_lon):
    """Calculate the (initial) bearing from start to end point.

    Reference: http://www.movable-type.co.uk/scripts/latlong.html
    """
    phi_1, phi_2 = radians(start_lat), radians(end_lat)
    delta_lambda = radians(end_lon - start_lon)
    y = sin(delta_lambda) * cos(phi_2)
    x = cos(phi_1)*sin(phi_2) - sin(phi_1)*cos(phi_2)*cos(delta_lambda)
    theta = atan2(y, x)

    return (degrees(theta) + 360) % 360


def cross_track_distance_from_point_to_path(
    point_lat, point_lon,
    path_start_lat, path_start_lon,
    path_end_lat, path_end_lon,
    radius=MAJOR_AXIS_MILES
):
    """Calculate (signed) distance from a point to a great circle defined by
    path_start and path_end.

    Reference: http://www.movable-type.co.uk/scripts/latlong.html
    """
    distance_from_start_to_point = vincenty_distance(
        path_start_lat, path_start_lon,
        point_lat, point_lon
    ) / radius
    bearing_from_start_to_point = radians(
        bearing(path_start_lat, path_start_lon, point_lat, point_lon)
    )
    bearing_from_start_to_end = radians(
        bearing(path_start_lat, path_start_lon, path_end_lat, path_end_lon)
    )

    return asin(
        sin(distance_from_start_to_point) * sin(
            bearing_from_start_to_point - bearing_from_start_to_end
        )
    ) * radius


# def vincenty_distance(lats_from, lons_from, alts_from, lats_to, lons_to, alts_to):
#     lats_mid = (lats_from + lats_to) / 2.0
#     alts_mid = ((alts_from + alts_to) / 2.0) / MILES_TO_FEET
#     earth_radii = earth_radius(lats_mid, alts_mid) + alts_mid

#     lats_to_in_radians = np.radians(lats_to)
#     lats_from_in_radians = np.radians(lats_from)
#     lons_diff_in_radians = np.radians(lons_to - lons_from)

#     return MILES_TO_FEET * np.arctan2(
#         np.sqrt(
#             (np.cos(lats_to_in_radians) * np.sin(lons_diff_in_radians))**2 +
#             (np.cos(lats_from_in_radians) * np.sin(lats_to_in_radians) - (np.sin(lats_from_in_radians) * np.cos(lats_to_in_radians) * np.cos(lons_diff_in_radians)))**2
#         ),
#         np.sin(lats_from_in_radians) * np.sin(lats_to_in_radians) + np.cos(lats_from_in_radians) * np.cos(lats_to_in_radians) * np.cos(lons_diff_in_radians)
#     ) * earth_radii


# def earth_radius(lats, alts):
#     lats_in_radians = np.radians(lats)

#     return np.sqrt(
#         ((EQUATOR_RADIUS_MILES**2 * np.cos(lats_in_radians))**2 + (POLAR_RADIUS_MILES**2 * np.sin(lats_in_radians))**2) /
#         ((EQUATOR_RADIUS_MILES * np.cos(lats_in_radians))**2 + (POLAR_RADIUS_MILES * np.sin(lats_in_radians))**2)
#     )
