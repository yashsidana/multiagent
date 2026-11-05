import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from src.api.routes import api_router
from src.rag.vector_store import vector_store
from src.rag.ingest import ingest_documents
from src.database.schema_inspector import schema_inspector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and teardown handler."""
    logger.info("Initializing %s v%s...", settings.PROJECT_NAME, settings.VERSION)

    # 1. Load or build FAISS vector index at startup
    loaded = vector_store.load()
    if not loaded:
        logger.info("Building initial FAISS index from documents directory...")
        ingest_documents()

    # 2. Pre-cache database schema
    try:
        schema_inspector.get_schema_summary()
        logger.info("Inspected and cached MySQL schema.")
    except Exception as e:
        logger.warning("Could not connect to MySQL at startup: %s", str(e))

    yield

    logger.info("Shutting down %s.", settings.PROJECT_NAME)


def create_app() -> FastAPI:
    """Factory function for FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Multi-Agent Business Insights Copilot (LangGraph, FAISS RAG, MySQL Text-to-SQL, FastAPI)",
        lifespan=lifespan
    )

    # Enable CORS for frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes under prefix
    app.include_router(api_router, prefix=settings.API_PREFIX)
    app.include_router(api_router)  # Also expose directly at root

    return app


app = create_app()

