from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from database import get_neo4j_driver, DATABASE
from decorators import role_required

bp = Blueprint('services', __name__)

@bp.route('/service_needed')
@role_required('job_seeker')
def index():
    driver = get_neo4j_driver()
    with driver.session(database=DATABASE) as session:
        # Collect categories and locations from service request nodes
        result = session.run("MATCH (s:ServiceRequest) RETURN DISTINCT s.category as category, s.location as location")
        categories = set()
        locations = set()
        for record in result:
            if record.get('category'):
                categories.add(record['category'])
            if record.get('location'):
                locations.add(record['location'])
        categories = sorted(list(categories))
        locations = sorted(list(locations))

        # Get all service requests with requester info and latitude/longitude
        result = session.run("""
            MATCH (s:ServiceRequest)
            OPTIONAL MATCH (s)<-[:REQUESTED]-(u:User)
            RETURN s { .*, latitude: s.latitude, longitude: s.longitude, client: u { .* } } as service
            ORDER BY s.created_at DESC
        """)
        services = [dict(record['service']) for record in result]

    return render_template('services/index.html',
                         services=services,
                         categories=categories,
                         locations=locations)

@bp.route('/service_needed/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        location = request.form.get('location')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        budget = request.form.get('budget')

        if not all([title, description, category, location, latitude, longitude]):
            flash('All fields are required', 'error')
            return redirect(url_for('services.create'))

        driver = get_neo4j_driver()
        with driver.session(database=DATABASE) as session:
            session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (s:Service {
                    id: randomUUID(),
                    title: $title,
                    description: $description,
                    category: $category,
                    location: $location,
                    latitude: $latitude,
                    longitude: $longitude,
                    budget: $budget,
                    status: 'open',
                    created_at: datetime()
                })
                CREATE (u)-[:REQUESTED]->(s)
            """, {
                'user_id': current_user.id,
                'title': title,
                'description': description,
                'category': category,
                'location': location,
                'latitude': float(latitude),
                'longitude': float(longitude),
                'budget': float(budget) if budget else None
            })

        flash('Service request created successfully', 'success')
        return redirect(url_for('services.index'))

    return render_template('services/create.html')

@bp.route('/api/search-services')
def search_services():
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
            conditions.append("toLower(s.title) CONTAINS $search_term OR toLower(s.description) CONTAINS $search_term")
            params["search_term"] = search_term
        
        if category:
            conditions.append("s.category = $category")
            params["category"] = category
            
        if location:
            conditions.append("s.location = $location")
            params["location"] = location
            
        where_clause = " AND ".join(conditions) if conditions else "true"
        
        # Count total results
        count_query = f"""
        MATCH (s:Service)
        WHERE {where_clause}
        RETURN count(s) as total
        """
        total = session.run(count_query, params).single()['total']
        
        # Get paginated results
        query = f"""
        MATCH (s:Service)
        WHERE {where_clause}
        RETURN s {{
            .*,
            requester: [(s)<-[:REQUESTED]-(u:User) | u.name][0]
        }} as service
        ORDER BY s.created_at DESC
        SKIP $skip
        LIMIT $limit
        """
        
        params.update({
            "skip": (page - 1) * per_page,
            "limit": per_page
        })
        
        results = session.run(query, params)
        services = [dict(record['service']) for record in results]
        
        return jsonify({
            'services': services,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        })
        query = """
        MATCH (s:ServiceRequest)
        WHERE 
            (toLower(s.type) CONTAINS $search OR 
             toLower(s.description) CONTAINS $search)
        """
        
        if category:
            query += " AND s.category = $category"
        if location:
            query += " AND s.location = $location"

        query += """
        OPTIONAL MATCH (c:Client)-[:REQUESTED]->(s)
        RETURN s {
            .*,
            client_name: CASE WHEN s.anonymous THEN null ELSE c.name END
        } as service
        ORDER BY s.created_at DESC
        """

        result = session.run(query, 
                           search=search_term,
                           category=category,
                           location=location)
        
        services = [dict(record['service']) for record in result]
        
    return jsonify({'services': services})