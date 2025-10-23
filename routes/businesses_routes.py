from flask import Blueprint, render_template, request, current_app
from neo4j import exceptions as neo4j_exceptions
from database import driver as neo4j_driver, DATABASE as NEO4J_DATABASE

businesses_bp = Blueprint('businesses', __name__)


def _record_to_dict(node):
    """Convert neo4j.Node to dict with string id for template safety."""
    data = dict(node)
    if 'id' in data and not isinstance(data['id'], str):
        data['id'] = str(data['id'])
    return data


@businesses_bp.route('/', methods=['GET'])
def list_business_owners():
    """List business owners from User nodes where role='business_owner'."""
    if not neo4j_driver:
        return render_template(
            'errors/500.html',
            error="Database connection not available"
        ), 500

    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    location = request.args.get('location', '').strip()

    owners = []
    categories = set()
    locations = set()

    try:
        with neo4j_driver.session(database=NEO4J_DATABASE) as session:
            # Get business owners
            owners_query = """
                MATCH (u:User)
                WHERE u.role = 'business_owner'
                WITH u,
                    COALESCE(u.business_name, COALESCE(u.first_name, '') + ' ' + COALESCE(u.last_name, '')) AS display_name,
                    COALESCE(u.city, '') AS city,
                    COALESCE(u.province, '') AS province,
                    COALESCE(u.location, '') AS location,
                    COALESCE(u.category, '') AS category
                WHERE
                    CASE WHEN $query <> '' THEN
                        toLower(display_name) CONTAINS toLower($query) OR toLower(COALESCE(u.description, '')) CONTAINS toLower($query)
                    ELSE true END
                    AND
                    CASE WHEN $category <> '' THEN category = $category ELSE true END
                    AND
                    CASE WHEN $location <> '' THEN
                        toLower(city) CONTAINS toLower($location) OR
                        toLower(province) CONTAINS toLower($location) OR
                        toLower(location) CONTAINS toLower($location)
                    ELSE true END
                RETURN u, display_name
                ORDER BY display_name
            """
            result = session.run(owners_query, {
                'query': query,
                'category': category,
                'location': location
            })

            for record in result:
                try:
                    u = _record_to_dict(record["u"])
                    # Ensure required fields have defaults
                    u['business_name'] = u.get('business_name') or f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
                    u['description'] = u.get('description') or 'No description available'
                    u['category'] = u.get('category') or 'Uncategorized'

                    # Build location string
                    city = u.get('city', '').strip()
                    province = u.get('province', '').strip()
                    if city or province:
                        loc = f"{city}{', ' if city and province else ''}{province}".strip()
                    else:
                        loc = u.get('location') or 'Location not specified'
                    u['location'] = loc

                    if loc:
                        locations.add(loc)

                    owners.append(u)
                except Exception as e:
                    print(f"Error processing business record: {str(e)}")
                    continue

            # Get all categories
            categories_result = session.run("""
                MATCH (u:User {role: 'business_owner'})
                WHERE u.category IS NOT NULL
                RETURN DISTINCT u.category as category
                ORDER BY category
            """)
            for record in categories_result:
                if record.get('category'):
                    categories.add(record['category'])

            # Get all locations
            locations_result = session.run("""
                MATCH (u:User {role: 'business_owner'})
                WHERE u.city IS NOT NULL OR u.province IS NOT NULL OR u.location IS NOT NULL
                RETURN DISTINCT 
                    CASE
                        WHEN u.city IS NOT NULL OR u.province IS NOT NULL
                        THEN COALESCE(u.city, '') + CASE 
                            WHEN u.city IS NOT NULL AND u.province IS NOT NULL THEN ', '
                            ELSE ''
                        END + COALESCE(u.province, '')
                        ELSE u.location
                    END as location
                ORDER BY location
            """)
            for record in locations_result:
                if record.get('location'):
                    locations.add(record['location'])

    except neo4j_exceptions.ServiceUnavailable:
        current_app.logger.exception('Neo4j service unavailable while listing business owners')
        return render_template(
            'errors/500.html',
            error="Database service is currently unavailable. Please try again later."
        ), 500
    except Exception:
        current_app.logger.exception('Unhandled exception in list_business_owners')
        return render_template(
            'errors/500.html',
            error="An unexpected error occurred. Please try again later."
        ), 500

    return render_template(
        'businesses.html',
        owners=owners,
        categories=sorted(categories),
        locations=sorted(locations),
        q=query,
        current_category=category or '',
        current_location=location or '',
    )
