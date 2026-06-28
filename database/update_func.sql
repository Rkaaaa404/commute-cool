CREATE OR REPLACE FUNCTION build_routing_topology() RETURNS void AS $$
BEGIN
    DROP TABLE IF EXISTS segments_noded CASCADE;

    -- Buat tabel noded dari segments yang valid
    CREATE TABLE segments_noded AS
    SELECT
        segment_id  AS id,
        segment_id  AS old_id,
        1           AS sub_id,
        NULL::integer AS source,
        NULL::integer AS target,
        length_m,
        geom
    FROM segments
    WHERE geom IS NOT NULL
      AND length_m IS NOT NULL
      AND length_m > 0;

    ALTER TABLE segments_noded ADD PRIMARY KEY (id);
    CREATE INDEX idx_segments_noded_geom ON segments_noded USING GIST (geom);
    CREATE INDEX idx_segments_noded_old_id ON segments_noded (old_id);

    -- Tolerance 0.0005° (~55m) untuk menggabungkan endpoint yang hampir bertemu
    PERFORM pgr_createTopology(
        'segments_noded',
        0.0005,
        'geom',
        'id',
        'source',
        'target',
        rows_where := 'true',
        clean := true
    );

    -- Add component_size column to vertices and populate it
    ALTER TABLE segments_noded_vertices_pgr ADD COLUMN IF NOT EXISTS component_size integer;

    WITH cc AS (
        SELECT node, count(*) OVER (PARTITION BY component) as sz
        FROM pgr_connectedComponents(
            'SELECT id, source::integer, target::integer, 1.0 as cost FROM segments_noded WHERE source IS NOT NULL AND target IS NOT NULL'
        )
    )
    UPDATE segments_noded_vertices_pgr v
    SET component_size = cc.sz
    FROM cc
    WHERE v.id = cc.node;

    RAISE NOTICE 'Routing topology built successfully (tolerance=0.0005)';
END;
$$ LANGUAGE plpgsql;
