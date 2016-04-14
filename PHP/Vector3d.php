<?php
/* - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  *
 * Vector handling functions                                          (c) Chris Veness 2011-2016  *
 *                                                                                   MIT Licence  *
 * www.movable-type.co.uk/scripts/geodesy/docs/module-vector3d.html                               *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  */


/**
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
 */
class Vector3d
{
    // Instance Variables
    private $x = 0.0;
    private $y = 0.0;
    private $z = 0.0;

    /**
     * Creates a 3-d vector.
     *
     * The vector may be normalized, or use x/y/z values for eg height relative to the sphere or
     * ellipsoid, distance from earth center, etc.
     *
     * @constructor
     * @param {number} x - X component of vector.
     * @param {number} y - Y component of vector.
     * @param {number} z - Z component of vector.
     */
    function Vector3d($x, $y, $z)
    {
        $this->x = $x;
        $this->y = $y;
        $this->z = $z;
    }


    /**
     * Adds supplied vector to ‘this’ vector.
     *
     * @param   {Vector3d} v - Vector to be added to this vector.
     * @returns {Vector3d} Vector representing sum of this and v.
     */
    function plus($v)
    {
        return new Vector3d($this->x + $v->x, $this->y + $v->y, $this->z + $v->z);
    }


    /**
     * Subtracts supplied vector from ‘this’ vector.
     *
     * @param   {Vector3d} v - Vector to be subtracted from this vector.
     * @returns {Vector3d} Vector representing difference between this and v.
     */
    function minus($v)
    {
        return new Vector3d($this->x - $v->x, $this->y - $v->y, $this->z - $v->z);
    }


    /**
     * Multiplies ‘this’ vector by a scalar value.
     *
     * @param   {number}   x - Factor to multiply this vector by.
     * @returns {Vector3d} Vector scaled by x.
     */
    function times($x)
    {
        return new Vector3d($this->x * $x, $this->y * x, $this->z * $x);
    }


    /**
     * Divides ‘this’ vector by a scalar value.
     *
     * @param   {number}   x - Factor to divide this vector by.
     * @returns {Vector3d} Vector divided by x.
     */
    function dividedBy($x)
    {
        return new Vector3d($this->x / $x, $this->y / $x, $this->z / $x);
    }


    /**
     * Multiplies ‘this’ vector by the supplied vector using dot (scalar) product.
     *
     * @param   {Vector3d} v - Vector to be dotted with this vector.
     * @returns {number} Dot product of ‘this’ and v.
     */
    function dot($v)
    {
        return $this->x*$v->x + $this->y*$v->y + $this->z*$v->z;
    }


    /**
     * Multiplies ‘this’ vector by the supplied vector using cross (vector) product.
     *
     * @param   {Vector3d} v - Vector to be crossed with this vector.
     * @returns {Vector3d} Cross product of ‘this’ and v.
     */
    function cross($v)
    {
        $x = $this->y*$v->z - $this->z*$v->y;
        $y = $this->z*$v->x - $this->x*$v->z;
        $z = $this->x*$v->y - $this->y*$v->x;

        return Vector3d(x, y, z);
    }


    /**
     * Negates a vector to point in the opposite direction
     *
     * @returns {Vector3d} Negated vector.
     */
    function negate()
    {
        return new Vector3d(-$this->x, -$this->y, -$this->z);
    }


    /**
     * Length (magnitude or norm) of ‘this’ vector
     *
     * @returns {number} Magnitude of this vector.
     */
    function length()
    {
        return sqrt($this->x*$this->x + $this->y*$this->y + $this->z*$this->z);
    }


    /**
     * Normalizes a vector to its unit vector
     * – if the vector is already unit or is zero magnitude, this is a no-op.
     *
     * @returns {Vector3d} Normalized version of this vector.
     */
    function unit()
    {
        $norm = $this->length();
        if ($norm == 1 or $norm == 0)  return $this;

        $x = $this->x / $norm;
        $y = $this->y / $norm;
        $z = $this->z / $norm;

        return new Vector3d($x, $y, $z);
    }


    /**
     * Calculates the angle between ‘this’ vector and supplied vector.
     *
     * @param   {Vector3d} v
     * @param   {Vector3d} [vSign] - If supplied (and out of plane of this and v), angle is signed +ve if
     *     this->v is clockwise looking along vSign, -ve in opposite direction (otherwise unsigned angle).
     * @returns {number} Angle (in radians) between this vector and supplied vector.
     */
    function angleTo($v, $vSign=NULL)
    {
        $sinTheta = $this->cross($v).length();
        $cosTheta = $this->dot($v);

        if ($vSign !== NULL) {
            // use vSign as reference to get sign of sinTheta
            $sinTheta = $this->cross($v)->dot($vSign) < 0 ? -$sinTheta : $sinTheta;
        }

        return atan2($sinTheta, $cosTheta);
    }


    /**
     * String representation of vector.
     *
     * @param   {number} [precision=5] - Number of decimal places to be used.
     * @returns {string} Vector represented as [x,y,z].
     */
    function __toString()
    {
        return "<{$this->x}, {$this->y}, {$this->z}>";
    }
}
?>