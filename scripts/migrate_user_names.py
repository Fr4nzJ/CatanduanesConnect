import os
import sys
from pathlib import Path

# Add parent directory to sys.path to import app modules
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

from models import User
from database import get_neo4j_driver, get_database_name
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_user_names():
    """Migrate existing users from single name field to separate name fields."""
    try:
        driver = get_neo4j_driver()
        database = get_database_name()
        
        with driver.session(database=database) as session:
            # First, get all users with the old name field
            result = session.run("""
                MATCH (u:User)
                WHERE u.name IS NOT NULL
                RETURN u
            """)
            
            users = list(result)
            logger.info(f"Found {len(users)} users to migrate")
            
            for record in users:
                user = record["u"]
                user_id = user["id"]
                full_name = user["name"].strip()
                name_parts = full_name.split()
                
                # Initialize name components
                first_name = name_parts[0] if name_parts else ""
                last_name = name_parts[-1] if len(name_parts) > 1 else ""
                middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
                suffix = None
                
                # Check for common suffixes in the last part
                common_suffixes = ["Jr.", "Sr.", "II", "III", "IV", "V"]
                if last_name in common_suffixes:
                    suffix = last_name
                    last_name = name_parts[-2] if len(name_parts) > 1 else ""
                    middle_name = " ".join(name_parts[1:-2]) if len(name_parts) > 3 else ""
                elif any(last_name.endswith(f" {suffix}") for suffix in common_suffixes):
                    for sfx in common_suffixes:
                        if last_name.endswith(f" {sfx}"):
                            suffix = sfx
                            last_name = last_name[:-len(sfx)].strip()
                            break
                
                # Update the user record
                session.run("""
                    MATCH (u:User {id: $id})
                    SET 
                        u.first_name = $first_name,
                        u.last_name = $last_name,
                        u.middle_name = $middle_name,
                        u.suffix = $suffix,
                        u.name = null
                """, {
                    "id": user_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "middle_name": middle_name if middle_name else None,
                    "suffix": suffix
                })
                
                logger.info(f"Migrated user {user_id}: '{full_name}' -> {first_name} {middle_name} {last_name} {suffix or ''}")
            
            logger.info("Migration completed successfully!")
            
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Starting user name migration...")
    migrate_user_names()
    logger.info("Migration script completed.")