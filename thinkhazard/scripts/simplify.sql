/*
Calculate approximative display resolution of passed geometry.
Note that some geometries cross the ante-meridian,
so we use minimal geodesic distance between bbox opposite corners.
*/
CREATE OR REPLACE FUNCTION datamart.resolution(
    geom geometry
) RETURNS double precision AS
$$
DECLARE
    distance double precision;
BEGIN

    distance = ST_Distance(
        ST_Point(ST_XMin(geom), ST_YMin(geom))::geography,
        ST_Point(ST_XMax(geom), ST_YMax(geom))::geography
    );
    RETURN distance / 250;
END;
$$
LANGUAGE plpgsql
IMMUTABLE
PARALLEL SAFE;

/*
Return simplify version of passed geometry for displaing at passed resolution.
Make buffer if needed depending on area and resolution.
*/
CREATE OR REPLACE FUNCTION datamart.simplify(
    admindiv datamart.administrativedivision,
    resolution double precision,
    parent datamart.administrativedivision DEFAULT NULL
) RETURNS geometry AS
$$
DECLARE
    name text;
    geom geometry;
    parent_geom geometry;
    area_ratio integer;
    area double precision;
    first_tolerance double precision;
    first_simplified geometry;
    simplified geometry;
BEGIN
    RAISE DEBUG 'Simplifying % - %, level %, % points for resolution % m',
        admindiv.code,
        CASE
            -- Handle wreid encoding error.
            WHEN admindiv.name LIKE 'Rumid%ahui' THEN 'Rumidahui'
            ELSE admindiv.name
        END,
        admindiv.leveltype_id,
        ST_NPoints(admindiv.geom),
        resolution;

    geom = ST_Transform(admindiv.geom, 3857);

    -- If we are threating parent resolution,
    -- use the parent area to get the same buffer for all geometries.
    IF parent IS NULL
    THEN
        parent_geom = geom;
    ELSE
        parent_geom = ST_Transform(parent.geom, 3857);
    END IF;

    area_ratio = 1000;  -- Minimum number of pixels
    RAISE DEBUG '  Area';
    area = ST_Area(parent_geom);

    RAISE DEBUG '    resolution: % km', resolution / 1000;
    RAISE DEBUG '    pixel size: % km²', pow(resolution, 2) / 1000000;
    RAISE DEBUG '    needed: % km²', pow(resolution, 2) * area_ratio / 1000000;
    RAISE DEBUG '    area: % km²', area / 1000000;

    IF area < pow(resolution, 2) * area_ratio
    THEN
        -- Simplify a bit first to prevent buffer to be too expensive.
        first_tolerance = datamart.resolution(admindiv.geom) / 10;
        RAISE DEBUG '  First simplification: %', first_tolerance;
        first_simplified = ST_Simplify(geom, first_tolerance);
        IF ST_NPoints(first_simplified) IS NULL
        THEN
            RAISE DEBUG '  First simplification returned null geometry';
            first_simplified = geom;
        ELSE
            RAISE DEBUG '  First simplification result: % points', ST_NPoints(first_simplified);
        END IF;

        -- Make the polygons a bit bigger.
        RAISE DEBUG '  Buffer';
        geom = ST_Buffer(first_simplified, resolution * 2);
    END IF;

    RAISE DEBUG '  Final simplification';
    simplified = ST_Simplify(geom, resolution / 2);
    IF geom IS NULL
    THEN
        simplified = geom;
    END IF;

    RAISE DEBUG '  Final result: % km² for % points',
        ST_Area(simplified) / 1000000,
        ST_NPoints(simplified);
    RETURN ST_Multi(simplified);
END;
$$
LANGUAGE plpgsql
IMMUTABLE
PARALLEL SAFE;

-- Update field geom_simplified
UPDATE datamart.administrativedivision AS admindiv
SET geom_simplified = datamart.simplify(
    admindiv.*,
    datamart.resolution(admindiv.geom)
);

-- Update field geom_simplified_for_parent
UPDATE datamart.administrativedivision AS admindiv
SET geom_simplified_for_parent = datamart.simplify(
    admindiv.*,
    datamart.resolution(parent.geom),
    parent.*
)
FROM datamart.administrativedivision AS parent
WHERE parent.code = admindiv.parent_code;

-- Remove functions to avoid errors with different users.
DROP FUNCTION datamart.resolution(
    geom geometry
);
DROP FUNCTION datamart.simplify(
    admindiv datamart.administrativedivision,
    resolution double precision,
    parent datamart.administrativedivision
);

