"""AWS Lambda entry point for the Teduh API.

Lifespan is disabled so the asyncpg pool is not opened/closed on every
invocation; ``api.db.get_pool()`` creates it lazily and the module-level pool
is reused across warm invocations.
"""

from mangum import Mangum

from api.main import app

handler = Mangum(app, lifespan="off")
