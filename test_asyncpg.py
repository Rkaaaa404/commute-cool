import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect("postgresql://cc_user:cc_dev_pass@localhost:5432/commute_cool")
    try:
        source = 5684
        target = 4880
        cost_sql = "COALESCE(s.length_m, 50) / 1.33"
        rows = await conn.fetch(f"""
            SELECT
                r.seq,
                r.edge as segment_id
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
        print("Success:", rows)
    except Exception as e:
        print("Error:", repr(e))
    finally:
        await conn.close()

asyncio.run(test())
