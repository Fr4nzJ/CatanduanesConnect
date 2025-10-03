import os
import logging
import time
from neo4j import GraphDatabase, exceptions as neo4j_exceptions
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

_driver = None
_database = os.getenv('NEO4J_DATABASE', 'neo4j')


def get_neo4j_driver(max_retries: int = 3, backoff: float = 1.0):
    """Return a singleton Neo4j driver, retrying on transient failures.

    Reads connection details from environment variables:
    - NEO4J_URI
    - NEO4J_USERNAME
    - NEO4J_PASSWORD
    """
    global _driver
    if _driver is not None:
        return _driver

    uri = os.getenv('NEO4J_URI')
    user = os.getenv('NEO4J_USERNAME')
    password = os.getenv('NEO4J_PASSWORD')

    if not all([uri, user, password]):
        logger.error('Missing Neo4j environment variables. NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD are required.')
        raise ValueError('Missing required Neo4j environment variables')

    attempt = 0
    while attempt < max_retries:
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            # quick smoke test
            with driver.session(database=_database) as session:
                session.run('RETURN 1').single()
            _driver = driver
            logger.info('Connected to Neo4j successfully')
            return _driver
        except neo4j_exceptions.ServiceUnavailable as e:
            attempt += 1
            logger.warning('Neo4j ServiceUnavailable on attempt %d/%d: %s', attempt, max_retries, str(e))
            time.sleep(backoff * attempt)
        except Exception as e:
            logger.error('Unexpected error connecting to Neo4j: %s', str(e), exc_info=True)
            raise

    logger.error('Exceeded retries connecting to Neo4j')
    raise neo4j_exceptions.ServiceUnavailable('Could not connect to Neo4j after retries')


def get_database_name():
    return _database
