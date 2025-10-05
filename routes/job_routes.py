from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user, login_required
from database import get_neo4j_driver, DATABASE
from decorators import role_required
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('jobs', __name__)
from decorators import role_required

@bp.route('/job_offers')
@role_required('job_seeker')
def index():
    driver = get_neo4j_driver()
    with driver.session(database=DATABASE) as session:
        # Get unique categories and locations from Job nodes
        result = session.run("MATCH (j:Job) RETURN DISTINCT j.category as category, j.location as location")
        categories = set()
        locations = set()
        for record in result:
            if record.get('category'):
                categories.add(record['category'])
            if record.get('location'):
                locations.add(record['location'])
        categories = sorted(list(categories))
        locations = sorted(list(locations))

    return render_template('jobs/index.html',
                         categories=categories,
                         locations=locations)


@bp.route('/job_offers/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        location = request.form.get('location')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        salary = request.form.get('salary')
        qualifications = request.form.get('qualifications')

        if not all([title, description, category, location, latitude, longitude]):
            flash('All fields are required', 'error')
            return redirect(url_for('jobs.create'))

        driver = get_neo4j_driver()
        with driver.session(database=DATABASE) as session:
            # Check if user owns a business
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:OWNS]->(b:Business)
                RETURN b
            """, {'user_id': current_user.id})
            
            business = result.single()
            if not business:
                flash('You must own a business to post job offers', 'error')
                return redirect(url_for('jobs.create'))

            # Create job offer
            session.run("""
                MATCH (b:Business)<-[:OWNS]-(u:User {id: $user_id})
                CREATE (j:Job {
                    id: randomUUID(),
                    title: $title,
                    description: $description,
                    category: $category,
                    location: $location,
                    latitude: $latitude,
                    longitude: $longitude,
                    salary: $salary,
                    qualifications: $qualifications,
                    status: 'open',
                    created_at: datetime()
                })
                CREATE (b)-[:POSTED]->(j)
            """, {
                'user_id': current_user.id,
                'title': title,
                'description': description,
                'category': category,
                'location': location,
                'latitude': float(latitude),
                'longitude': float(longitude),
                'salary': float(salary) if salary else None,
                'qualifications': qualifications.split('\n') if qualifications else []
            })

        flash('Job offer created successfully', 'success')
        return redirect(url_for('jobs.index'))

    return render_template('jobs/create.html')

@bp.route('/api/search-jobs')
def search_jobs():
    try:
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
                conditions.append("toLower(j.title) CONTAINS $search_term OR toLower(j.description) CONTAINS $search_term")
                params["search_term"] = search_term
            
            if category:
                conditions.append("j.category = $category")
                params["category"] = category
                
            if location:
                conditions.append("j.location = $location")
                params["location"] = location
                
            where_clause = " AND ".join(conditions) if conditions else "true"
            
            # Count total results
            count_query = f"""
            MATCH (j:Job)
            WHERE {where_clause}
            RETURN count(j) as total
            """
            total = session.run(count_query, params).single()['total']
            
            # Get paginated results
            query = f"""
            MATCH (j:Job)
            WHERE {where_clause}
            OPTIONAL MATCH (j)<-[:POSTED]-(b:Business)
            RETURN j {{
                .*,
                latitude: j.latitude,
                longitude: j.longitude,
                business: b {{ .* }}
            }} as job
            ORDER BY j.created_at DESC
            SKIP $skip
            LIMIT $limit
            """
            
            params.update({
                "skip": (page - 1) * per_page,
                "limit": per_page
            })
            
            results = session.run(query, params)
            jobs = [dict(record['job']) for record in results]
            
            return jsonify({
                'jobs': jobs,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            })
    except Exception as e:
        logger.error(f"Error searching jobs: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@bp.route('/jobs', endpoint='jobs')
def list_jobs():
    """List all job posts with optional filtering."""
    try:
        # Get filter parameters
        search = request.args.get('search', '').lower()
        category = request.args.get('category', '')
        location = request.args.get('location', '')
        
        with get_neo4j_driver().session(database=DATABASE) as session:
            result = session.run("""
                MATCH (u:User)-[:POSTED]->(j:JobPost)
                WHERE 
                    (toLower(j.title) CONTAINS $search OR 
                     toLower(j.description) CONTAINS $search)
                    AND ($category = '' OR j.category = $category)
                    AND ($location = '' OR j.location = $location)
                RETURN j, u
                ORDER BY j.created_at DESC
            """, search=search, category=category, location=location)
            
            jobs = [{
                **dict(record["j"]),
                "owner": dict(record["u"])
            } for record in result]
            
            # For AJAX requests, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"jobs": jobs})
                
            # For direct browser requests, render template
            return render_template('jobs/index.html', 
                                jobs=jobs,
                                search=search,
                                category=category,
                                location=location)
    except Exception as e:
        logger.error(f"Error listing jobs: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@bp.route('/jobs/<job_id>')
def view_job(job_id):
    """View a single job post."""
    try:
        with get_neo4j_driver().session(database=DATABASE) as session:
            result = session.run("""
                MATCH (u:User)-[:POSTED]->(j:JobPost)
                WHERE j.id = $job_id
                RETURN j, u
            """, job_id=job_id)
            
            record = result.single()
            if not record:
                return jsonify({"error": "Job not found"}), 404
                
            job = {
                **dict(record["j"]),
                "owner": dict(record["u"])
            }
            
            # For AJAX requests, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"job": job})
                
            # For direct browser requests, render template
            return render_template('jobs/details.html', job=job)
    except Exception as e:
        logger.error(f"Error viewing job: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@bp.route('/jobs/categories')
def get_categories():
    """Get all unique job categories."""
    try:
        with get_neo4j_driver().session(database=DATABASE) as session:
            result = session.run("""
                MATCH (j:JobPost)
                RETURN DISTINCT j.category
                ORDER BY j.category
            """)
            categories = [record["j.category"] for record in result]
            return jsonify({"categories": categories})
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@bp.route('/jobs/locations')
def get_locations():
    """Get all unique job locations."""
    try:
        with get_neo4j_driver().session(database=DATABASE) as session:
            result = session.run("""
                MATCH (j:JobPost)
                RETURN DISTINCT j.location
                ORDER BY j.location
            """)
            locations = [record["j.location"] for record in result]
            return jsonify({"locations": locations})
    except Exception as e:
        logger.error(f"Error getting locations: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500