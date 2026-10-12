import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.engine import make_url
import logging
from ..config import settings

logger = logging.getLogger(__name__)

class DatabasePool:
    def __init__(self):
        self.engine = None
        self.session_factory = None
        
    async def initialize(self):
        """Initialize database connection pool (once; later calls are no-ops)"""
        if self.session_factory:
            return
        try:
            # DATABASE_URL is the only DB setting that exists (config.py / docker-compose).
            # SQLAlchemy needs the +asyncpg driver in the scheme for the async engine.
            database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            
            # No poolclass: async engines default to AsyncAdaptedQueuePool (QueuePool is sync-only)
            self.engine = create_async_engine(
                database_url,
                pool_size=20,  # Number of connections to maintain
                max_overflow=30,  # Additional connections when needed
                pool_pre_ping=True,  # Validate connections
                pool_recycle=3600,  # Recycle connections every hour
                # Fail fast instead of hanging when the DB is stuck: the request becomes a 503.
                pool_timeout=5,  # seconds to wait for a free pooled connection
                connect_args={
                    "timeout": 5,  # asyncpg: seconds to establish a connection
                    "command_timeout": 5,  # asyncpg: seconds per query (dashboard queries take ms)
                },
                echo=False  # Set to True for SQL debugging
            )
            
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("✅ Database connection pool initialized")
            
        except Exception as e:
            # Log the error class and a password-masked URL only: the raw exception or URL
            # could echo the DSN, password included, into the logs.
            logger.error(f"❌ Database pool initialization failed ({e.__class__.__name__}) for {_safe_db_url()}")
            self.engine = None
            self.session_factory = None
    
    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
    
    def get_session(self) -> AsyncSession:
        """Get database session from pool. Use as: async with db_pool.get_session() as session"""
        if not self.session_factory:
            raise Exception("Database pool not initialized")
        return self.session_factory()

def _safe_db_url() -> str:
    """DATABASE_URL with the password hidden, for log lines."""
    try:
        return make_url(settings.database_url).render_as_string(hide_password=True)
    except Exception:
        return "<unparseable DATABASE_URL>"

# Global database pool instance
db_pool = DatabasePool()

async def get_db_session() -> AsyncSession:
    """Dependency to get database session"""
    async with db_pool.get_session() as session:
        yield session
