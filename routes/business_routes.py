from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from database import get_neo4j_driver, DATABASE

bp = Blueprint('businesses', __name__)


@bp.route('/businesses')
def index():
    """Render the businesses listing page using User nodes with role='business_owner'."""
    driver = get_neo4j_driver()
    with driver.session(database=DATABASE) as session:
        result = session.run("""
            MATCH (u:User)
            WHERE u.role = 'business_owner'
            RETURN u { .*,
                business_name: coalesce(u.business_name, u.first_name + ' ' + u.last_name),
                location: coalesce(u.location, u.province, u.city, ''),
                latitude: u.latitude,
                longitude: u.longitude
            } as business
            ORDER BY business.business_name
        """)
        businesses = [dict(record['business']) for record in result]

        # categories and locations for filters
        result = session.run("MATCH (u:User) WHERE u.role = 'business_owner' RETURN DISTINCT u.category as category")
        categories = [record['category'] for record in result if record['category']]

        result = session.run("MATCH (u:User) WHERE u.role = 'business_owner' RETURN DISTINCT coalesce(u.location, u.province, u.city) as location")
        locations = [record['location'] for record in result if record['location']]

    return render_template('businesses/businesses.html', businesses=businesses, categories=categories, locations=locations)


@bp.route('/api/search-businesses')
def search_businesses():
    q = request.args.get('q', '').strip().lower()
    category = request.args.get('category', '').strip()
    location = request.args.get('location', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 20

    driver = get_neo4j_driver()
    with driver.session(database=DATABASE) as session:
        conditions = ["u.role = 'business_owner'"]
        params = {}

        if q:
            conditions.append("(toLower(coalesce(u.business_name, u.first_name + ' ' + u.last_name)) CONTAINS $q OR toLower(coalesce(u.description, '')) CONTAINS $q)")
            params['q'] = q

        if category:
            conditions.append("u.category = $category")
            params['category'] = category

        if location:
            conditions.append("(coalesce(u.location, u.province, u.city) = $location)")
            params['location'] = location

        where_clause = ' AND '.join(conditions)

        count_query = f"""
        MATCH (u:User)
        WHERE {where_clause}
        RETURN count(u) as total
        """
        total = session.run(count_query, params).single()['total']

        query = f"""
        MATCH (u:User)
        WHERE {where_clause}
        RETURN u {{ .*,
            business_name: coalesce(u.business_name, u.first_name + ' ' + u.last_name),
            location: coalesce(u.location, u.province, u.city, ''),
            latitude: u.latitude,
            longitude: u.longitude
        }} as business
        ORDER BY business.business_name
        SKIP $skip
        LIMIT $limit
        """

        params.update({'skip': (page - 1) * per_page, 'limit': per_page})
        results = session.run(query, params)
        businesses = [dict(record['business']) for record in results]

        return jsonify({'businesses': businesses, 'total': total, 'pages': (total + per_page - 1) // per_page})