-- ============================================================
-- Teduh: Rebuild Routing Topology
-- Jalankan ini setelah data OSM di-ingested ke tabel segments.
--
-- Cara jalankan:
--   docker exec teduh_db psql -U cc_user -d commute_cool \
--     -f /tmp/rebuild_topology.sql
--
-- Atau via API: POST /api/admin/rebuild-topology
-- ============================================================

\timing on

DO $$
BEGIN
    RAISE NOTICE '=== MEMBANGUN TOPOLOGI ROUTING ===';
    RAISE NOTICE 'Tolerance: 0.0005 derajat (~55 meter)';
    RAISE NOTICE 'Input: % segmen', (SELECT COUNT(*) FROM segments);
END $$;

-- Bersihkan tabel lama (termasuk tabel vertices pgRouting)
DROP TABLE IF EXISTS segments_noded CASCADE;

-- Buat tabel segments_noded sebagai copy 1-to-1 dari segments.
-- Data OSM pedestrian sudah dipotong per intersection, sehingga
-- noding ulang tidak diperlukan. pgr_createTopology dengan
-- tolerance 0.0005° (~55m) cukup untuk menggabungkan endpoint
-- yang hampir bertemu.
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

DO $$
BEGIN
    RAISE NOTICE 'segments_noded dibuat: % edges', (SELECT COUNT(*) FROM segments_noded);
    RAISE NOTICE 'Menjalankan pgr_createTopology dengan tolerance=0.0005...';
END $$;

-- Bangun topologi: isi kolom source dan target, buat tabel vertices
-- Tolerance 0.0005° (~55m) lebih besar dari default (0.0001°/11m)
-- agar endpoint segmen yang hampir bertemu bisa digabungkan.
SELECT pgr_createTopology(
    'segments_noded',
    0.0005,          -- tolerance ~55 meter
    'geom',
    'id',
    'source',
    'target',
    rows_where := 'true',
    clean := true    -- reset source/target sebelum rebuild
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

DO $$
DECLARE
    v_edges   bigint;
    v_verts   bigint;
    v_null    bigint;
    v_main_cc bigint;
BEGIN
    SELECT COUNT(*) INTO v_edges FROM segments_noded;
    SELECT COUNT(*) INTO v_verts FROM segments_noded_vertices_pgr;
    SELECT COUNT(*) INTO v_null FROM segments_noded WHERE source IS NULL OR target IS NULL;
    SELECT MAX(cnt) INTO v_main_cc
      FROM (
        SELECT component, COUNT(*) AS cnt
        FROM pgr_connectedComponents(
          'SELECT id, source::integer, target::integer,
                  length_m AS cost, length_m AS reverse_cost
           FROM segments_noded
           WHERE source IS NOT NULL AND target IS NOT NULL'
        )
        GROUP BY component
      ) cc;

    RAISE NOTICE '=== HASIL REBUILD TOPOLOGI ===';
    RAISE NOTICE 'Total edges       : %', v_edges;
    RAISE NOTICE 'Total vertices    : %', v_verts;
    RAISE NOTICE 'NULL source/target: %', v_null;
    RAISE NOTICE 'Komponen terbesar : % nodes', v_main_cc;
END $$;

-- Tampilkan ringkasan
SELECT COUNT(*) AS noded_edges    FROM segments_noded;
SELECT COUNT(*) AS noded_vertices FROM segments_noded_vertices_pgr;
SELECT COUNT(*) AS null_source    FROM segments_noded WHERE source IS NULL;
