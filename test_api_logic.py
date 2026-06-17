import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect("postgresql://cc_user:cc_dev_pass@localhost:5432/commute_cool")
    try:
        origin_lng, origin_lat = 112.7664126, -7.2748124
        dest_lng, dest_lat = 112.7663329, -7.2751945
        
        row_o = await conn.fetchrow("SELECT id FROM segments_vertices_pgr ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326) LIMIT 1", origin_lng, origin_lat)
        row_d = await conn.fetchrow("SELECT id FROM segments_vertices_pgr ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326) LIMIT 1", dest_lng, dest_lat)
        
        print("Origin node:", row_o["id"] if row_o else None)
        print("Dest node:", row_d["id"] if row_d else None)
        
        source = row_o["id"]
        target = row_d["id"]
        
        cost_sql = "COALESCE(ew.total_cost, COALESCE(s.length_m, 50) / 1.33)"
        
        rows = await conn.fetch(f"""
            SELECT r.seq, r.edge as segment_id
            FROM pgr_dijkstra(
                'SELECT segment_id as id, source::bigint, target::bigint,
                        {cost_sql} as cost,
                        {cost_sql} as reverse_cost
                 FROM segments s
                 LEFT JOIN LATERAL (
                     SELECT total_cost FROM edge_weights
                     WHERE segment_id = s.segment_id
                     ORDER BY valid_from DESC LIMIT 1
                 ) ew ON true',
                $1::bigint, $2::bigint, directed := false
            ) r
            WHERE r.edge > 0
            ORDER BY r.seq
        """, source, target)
        print("Route found, rows:", len(rows))
    except Exception as e:
        print("Error:", repr(e))
    finally:
        await conn.close()

asyncio.run(test())
