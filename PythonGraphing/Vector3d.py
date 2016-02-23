#coding: utf-8
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  #
# Vector handling functions                                          (c) Chris Veness 2011-2016  #
#                                                                                   MIT Licence  #
# www.movable-type.co.uk/scripts/geodesy/docs/module-vector3d.html                               #
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  #

import math


'''
 * Library of 3-d vector manipulation routines.
 *
 * In a geodesy context, these vectors may be used to represent:
 *  - n-vector representing a normal to point on Earth's surface
 *  - earth-centered, earth fixed vector (≡ Gade’s ‘p-vector’)
 *  - great circle normal to vector (on spherical earth model)
 *  - motion vector on Earth's surface
 *  - etc
 *
 * Functions return vectors as return results, so that operations can be chained.
 * @example var v = v1.cross(v2).dot(v3) // ≡ v1×v2⋅v3
 *
 * @module vector3d
'''
class Vector3d(object):
    x, y, z = 0.0, 0.0, 0.0

    '''
     * Creates a 3-d vector.
     *
     * The vector may be normalized, or use x/y/z values for eg height relative to the sphere or
     * ellipsoid, distance from earth center, etc.
     *
     * @constructor
     * @param {number} x - X component of vector.
     * @param {number} y - Y component of vector.
     * @param {number} z - Z component of vector.
    '''
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z


    '''
     * Adds supplied vector to ‘this’ vector.
     *
     * @param   {Vector3d} v - Vector to be added to this vector.
     * @returns {Vector3d} Vector representing sum of this and v.
    '''
    def plus(self, v):
        return Vector3d(self.x + v.x, self.y + v.y, self.z + v.z)


    '''
     * Subtracts supplied vector from ‘this’ vector.
     *
     * @param   {Vector3d} v - Vector to be subtracted from this vector.
     * @returns {Vector3d} Vector representing difference between this and v.
    '''
    def minus(self, v):
        return Vector3d(self.x - v.x, self.y - v.y, self.z - v.z)


    '''
     * Multiplies ‘this’ vector by a scalar value.
     *
     * @param   {number}   x - Factor to multiply this vector by.
     * @returns {Vector3d} Vector scaled by x.
    '''
    def times(self, x):
        return Vector3d(self.x * x, self.y * x, self.z * x)


    '''
     * Divides ‘this’ vector by a scalar value.
     *
     * @param   {number}   x - Factor to divide this vector by.
     * @returns {Vector3d} Vector divided by x.
    '''
    def dividedBy(self, x):
        return Vector3d(self.x / x, self.y / x, self.z / x)


    '''
     * Multiplies ‘this’ vector by the supplied vector using dot (scalar) product.
     *
     * @param   {Vector3d} v - Vector to be dotted with this vector.
     * @returns {number} Dot product of ‘this’ and v.
    '''
    def dot(self, v):
        return self.x*v.x + self.y*v.y + self.z*v.z


    '''
     * Multiplies ‘this’ vector by the supplied vector using cross (vector) product.
     *
     * @param   {Vector3d} v - Vector to be crossed with this vector.
     * @returns {Vector3d} Cross product of ‘this’ and v.
    '''
    def cross(self, v):
        x = self.y*v.z - self.z*v.y
        y = self.z*v.x - self.x*v.z
        z = self.x*v.y - self.y*v.x

        return Vector3d(x, y, z)


    '''
     * Negates a vector to point in the opposite direction
     *
     * @returns {Vector3d} Negated vector.
    '''
    def negate(self):
        return Vector3d(-self.x, -self.y, -self.z)


    '''
     * Length (magnitude or norm) of ‘this’ vector
     *
     * @returns {number} Magnitude of this vector.
    '''
    def length(self):
        return math.sqrt(self.x*self.x + self.y*self.y + self.z*self.z)


    '''
     * Normalizes a vector to its unit vector
     * – if the vector is already unit or is zero magnitude, this is a no-op.
     *
     * @returns {Vector3d} Normalized version of this vector.
    '''
    def unit(self):
        norm = self.length()
        if norm == 1 or norm == 0: return self

        x = self.x / norm
        y = self.y / norm
        z = self.z / norm

        return Vector3d(x, y, z)


    '''
     * Calculates the angle between ‘this’ vector and supplied vector.
     *
     * @param   {Vector3d} v
     * @param   {Vector3d} [vSign] - If supplied (and out of plane of this and v), angle is signed +ve if
     *     this->v is clockwise looking along vSign, -ve in opposite direction (otherwise unsigned angle).
     * @returns {number} Angle (in radians) between this vector and supplied vector.
    '''
    def angleTo(self, v, vSign=None):
        sinTheta = self.cross(v).length()
        cosTheta = self.dot(v)

        if vSign is not None:
            # use vSign as reference to get sign of sinTheta
            sinTheta = -sinTheta if self.cross(v).dot(vSign) < 0 else sinTheta

        return math.atan2(sinTheta, cosTheta)


    '''
     * String representation of vector.
     *
     * @param   {number} [precision=5] - Number of decimal places to be used.
     * @returns {string} Vector represented as [x,y,z].
    '''
    def toString(self, precision=None):
        p = 5 if precision is None else precision
        str = '<%.{0}f, %.{0}f, %.{0}f>'.format(p)
        return str % (self.x, self.y, self.z)
