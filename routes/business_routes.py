from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from database import get_neo4j_driver, DATABASE

bp = Blueprint('businesses', __name__)

@bp.route('/businesses')
def index():
    driver = get_neo4j_driver()
    with driver.session(database=DATABASE) as session:
        # Get all businesses with their jobs
        result = session.run("""
            MATCH (b:Business)
            OPTIONAL MATCH (b)-[:POSTED]->(j:Job)
            WITH b, collect({
                title: j.title,
                qualifications: j.qualifications
            }) as jobs
            RETURN b {
                .*,
                jobs: jobs
            } as business
            ORDER BY b.name
        """)
        businesses = [dict(record['business']) for record in result]

        # Get unique categories
        result = session.run("MATCH (b:Business) RETURN DISTINCT b.category as category")
        categories = [record['category'] for record in result if record['category']]

        # Get unique locations
        result = session.run("MATCH (b:Business) RETURN DISTINCT b.location as location")
        locations = [record['location'] for record in result if record['location']]

    return render_template('businesses/index.html',
                         businesses=businesses,
                         categories=categories,
                         locations=locations)

@bp.route('/api/search-businesses')
def search_businesses():
    search_term = request.args.get('q', '').lower()
    category = request.args.get('category', '')
    location = request.args.get('location', '')
    page = int(request.args.get('page', 1))
    per_page = 10

    driver = get_neo4j_driver()
    with driver.session(database=DATABASE) as session:
        # Build WHERE clause based on filters
        conditions = []
        params = {}
        
        if search_term:
            conditions.append("toLower(b.name) CONTAINS $search_term OR toLower(b.description) CONTAINS $search_term")
            params["search_term"] = search_term
        
        if category:
            conditions.append("b.category = $category")
            params["category"] = category
            
        if location:
            conditions.append("b.location = $location")
            params["location"] = location
            
        where_clause = " AND ".join(conditions) if conditions else "true"
        
        # Count total results
        count_query = f"""
        MATCH (b:Business)
        WHERE {where_clause}
        RETURN count(b) as total
        """
        total = session.run(count_query, params).single()['total']
        
        # Get paginated results
        query = f"""
        MATCH (b:Business)
        WHERE {where_clause}
        RETURN b {{
            .*,
            owner: [(b)<-[:OWNS]-(u:User) | u.name][0]
        }} as business
        ORDER BY b.name
        SKIP $skip
        LIMIT $limit
        """
        
        params.update({
            "skip": (page - 1) * per_page,
            "limit": per_page
        })
        
        results = session.run(query, params)
        businesses = [dict(record['business']) for record in results]
        
        return jsonify({
            'businesses': businesses,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        })
            (toLower(b.name) CONTAINS $search OR 
             toLower(b.description) CONTAINS $search OR
             EXISTS {
                 MATCH (b)-[:POSTED]->(j:Job)
                 WHERE toLower(j.title) CONTAINS $search
             }
            )
        """
        
        if category:
            query += " AND b.category = $category"
        if location:
            query += " AND b.location = $location"

        query += """
        OPTIONAL MATCH (b)-[:POSTED]->(j:Job)
        WITH b, collect({
            title: j.title,
            qualifications: j.qualifications
        }) as jobs
        RETURN b {
            .*,
            jobs: jobs
        } as business
        ORDER BY b.name
        """

        result = session.run(query, 
                           search=search_term,
                           category=category,
                           location=location)
        
        businesses = [dict(record['business']) for record in result]
        
    return jsonify({'businesses': businesses})