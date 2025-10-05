from flask import Blueprint, render_template, request, jsonify
from neo4j import exceptions as neo4j_exceptions

# Prefer importing the shared Neo4j driver from the central database module
from database import driver as neo4j_driver, DATABASE as NEO4J_DATABASE


businesses_bp = Blueprint('businesses', __name__)


def _record_to_dict(node):
    # Convert neo4j.Node to plain dict with id included if present
    data = dict(node)
    # ensure string types for safety in templates
    if 'id' in data and not isinstance(data['id'], str):
        data['id'] = str(data['id'])
    return data


@businesses_bp.route('/', methods=['GET'])
def list_business_owners():
    """List business owners from User nodes where role='business_owner'.

    Supports optional server-side filters via query params:
    - q: search by business_name or description
    - category: exact match on category
    - location: matches city or province (case-insensitive contains)
    """
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    location = request.args.get('location', '').strip()

    cypher_conditions = ["u.role = 'business_owner'"]
    params = {}

    if query:
        cypher_conditions.append("(toLower(u.business_name) CONTAINS toLower($q) OR toLower(u.description) CONTAINS toLower($q))")
        params['q'] = query

    if category:
        cypher_conditions.append("u.category = $category")
        params['category'] = category

    if location:
        # match city or province via contains to be forgiving
        cypher_conditions.append("(toLower(coalesce(u.city,'')) CONTAINS toLower($location) OR toLower(coalesce(u.province,'')) CONTAINS toLower($location) OR toLower(coalesce(u.location,'')) CONTAINS toLower($location))")
        params['location'] = location

    where_clause = " AND ".join(cypher_conditions)

    owners = []
    categories = set()
    locations = set()

    try:
        with neo4j_driver.session(database=NEO4J_DATABASE) as session:
            result = session.run(
                f"""
                MATCH (u:User)
                WHERE {where_clause}
                RETURN u ORDER BY toLower(u.business_name)
                """,
                **params,
            )
            for record in result:
                u = _record_to_dict(record["u"])  # neo4j.Node -> dict
                owners.append(u)
                if u.get('category'):
                    categories.add(u['category'])
                # derive a simple location label for filter list
                loc_label = (
                    (u.get('city') or '') + (', ' if u.get('city') and u.get('province') else '') + (u.get('province') or '')
                ).strip(', ')
                if loc_label:
                    locations.add(loc_label)
                elif u.get('location'):
                    locations.add(u['location'])

    except neo4j_exceptions.ServiceUnavailable as e:
        return render_template('businesses.html', owners=[], categories=[], locations=[], error=str(e))
    except Exception as e:
        return render_template('businesses.html', owners=[], categories=[], locations=[], error=str(e))

    # Sort filter values for stable UI
    categories_list = sorted(categories)
    locations_list = sorted(locations)

    return render_template(
        'businesses.html',
        owners=owners,
        categories=categories_list,
        locations=locations_list,
        q=query,
        current_category=category or '',
        current_location=location or '',
    )


