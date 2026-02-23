"""Amazon FBA Agent Crew - Application Entry Point."""
import asyncio
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from db.database import Base, get_engine
from gateway.api import app as fastapi_app
from scheduler.jobs import create_scheduler


def init_db():
    """Create all database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("[DB] Tables created.")


async def start():
    """Start the application: API server + scheduler."""
    init_db()

    scheduler = create_scheduler()
    scheduler.start()
    print("[Scheduler] Started with scheduled jobs.")

    config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
    server = uvicorn.Server(config)
    print("[API] Starting on port 8000...")
    await server.serve()


def main():
    asyncio.run(start())


if __name__ == "__main__":
    main()
