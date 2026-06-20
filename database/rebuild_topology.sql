CREATE OR REPLACE FUNCTION build_routing_topology() RETURNS void AS $$
BEGIN
    DROP TABLE IF EXISTS segments_noded CASCADE;
    PERFORM pgr_nodeNetwork('segments', 0.0001, 'segment_id', 'geom', 'segments_noded');
    PERFORM pgr_createTopology('segments_noded', 0.0001, 'geom', 'id');
    PERFORM pgr_analyzeGraph('segments_noded', 0.0001, 'geom', 'id');
    RAISE NOTICE 'Routing topology built successfully (pgr_nodeNetwork)';
END;
$$ LANGUAGE plpgsql;

SELECT build_routing_topology();
SELECT COUNT(*) AS noded_segments FROM segments_noded;
SELECT COUNT(*) AS noded_nodes FROM segments_noded_vertices_pgr;
