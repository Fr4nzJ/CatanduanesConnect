from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from utils.decorators import admin_required
from database import driver as neo4j_driver, DATABASE as NEO4J_DATABASE


admin = Blueprint("admin", __name__, url_prefix="/admin")


@admin.route("/dashboard")
@login_required
@admin_required
def dashboard():
    stats = {
        "total_users": 0,
        "job_seekers": 0,
        "business_owners": 0,
        "clients": 0,
        "pending_verifications": 0,
        "active_jobs": 0,
        "active_services": 0,
    }
    with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        row = session.run(
            """
            MATCH (u:User)
            RETURN
                count(u) AS total_users,
                count(CASE WHEN u.role='job_seeker' THEN 1 END) AS job_seekers,
                count(CASE WHEN u.role='business_owner' THEN 1 END) AS business_owners,
                count(CASE WHEN u.role='client' THEN 1 END) AS clients,
                count(CASE WHEN u.verification_status='pending_verification' THEN 1 END) AS pending_verifications
            """
        ).single()
        if row:
            stats.update({k: row[k] or 0 for k in stats.keys() if k in row.keys()})

        jobs_row = session.run(
            """
            MATCH (j:Job)
            RETURN count(j) AS active_jobs
            """
        ).single()
        if jobs_row:
            stats["active_jobs"] = jobs_row["active_jobs"] or 0

        svc_row = session.run(
            """
            MATCH (s:ServiceRequest)
            RETURN count(s) AS active_services
            """
        ).single()
        if svc_row:
            stats["active_services"] = svc_row["active_services"] or 0

    return render_template("admin/dashboard.html", stats=stats)


@admin.route("/users")
@login_required
@admin_required
def users():
    role = request.args.get("role")
    status = request.args.get("status")
    q = request.args.get("q", "").strip()

    conditions = []
    params = {}
    if role:
        conditions.append("u.role = $role")
        params["role"] = role
    if status:
        conditions.append("u.verification_status = $status")
        params["status"] = status
    if q:
        conditions.append("toLower(u.email) CONTAINS toLower($q) OR toLower(coalesce(u.first_name,'')) CONTAINS toLower($q) OR toLower(coalesce(u.last_name,'')) CONTAINS toLower($q)")
        params["q"] = q

    where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    users = []
    with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        res = session.run(
            f"""
            MATCH (u:User){where_clause}
            RETURN u ORDER BY toLower(u.email)
            """,
            **params,
        )
        for rec in res:
            users.append(dict(rec["u"]))

    return render_template("admin/users.html", users=users, q=q, role=role, status=status)


@admin.route("/verifications", methods=["GET", "POST"])
@login_required
@admin_required
def verifications():
    if request.method == "POST":
        email = request.form.get("email")
        action = request.form.get("action")
        if email and action in {"approve", "reject"}:
            new_status = "verified" if action == "approve" else "rejected"
            with neo4j_driver.session(database=NEO4J_DATABASE) as session:
                session.run(
                    """
                    MATCH (u:User {email: $email})
                    SET u.verification_status = $status
                    RETURN u
                    """,
                    email=email,
                    status=new_status,
                )
            flash("Status updated.", "success")
        return redirect(url_for("admin.verifications"))

    pending = []
    with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        res = session.run(
            """
            MATCH (u:User)
            WHERE u.verification_status = 'pending_verification'
            RETURN u ORDER BY toLower(u.email)
            """
        )
        for rec in res:
            pending.append(dict(rec["u"]))

    return render_template("admin/verifications.html", users=pending)


@admin.route("/jobs")
@login_required
@admin_required
def jobs():
    jobs = []
    with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        res = session.run(
            """
            MATCH (j:Job)-[:POSTED_BY]->(u:User)
            RETURN j, u ORDER BY j.created_at DESC
            """
        )
        for rec in res:
            j = dict(rec["j"]) ; j["poster"] = dict(rec["u"]) ; jobs.append(j)
    return render_template("admin/jobs.html", jobs=jobs)


@admin.route("/services")
@login_required
@admin_required
def services():
    services = []
    with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        res = session.run(
            """
            MATCH (s:ServiceRequest)-[:POSTED_BY]->(u:User)
            RETURN s, u ORDER BY s.created_at DESC
            """
        )
        for rec in res:
            s = dict(rec["s"]) ; s["client"] = dict(rec["u"]) ; services.append(s)
    return render_template("admin/services.html", services=services)


@admin.route("/reports")
@login_required
@admin_required
def reports():
    data = {
        "verified_users": 0,
        "pending_users": 0,
        "active_jobs": 0,
        "active_services": 0,
    }
    with neo4j_driver.session(database=NEO4J_DATABASE) as session:
        row = session.run(
            """
            MATCH (u:User)
            RETURN
              count(CASE WHEN u.verification_status='verified' THEN 1 END) AS verified_users,
              count(CASE WHEN u.verification_status='pending_verification' THEN 1 END) AS pending_users
            """
        ).single()
        if row:
            data["verified_users"] = row["verified_users"] or 0
            data["pending_users"] = row["pending_users"] or 0

        row = session.run("MATCH (j:Job) RETURN count(j) AS c").single()
        if row:
            data["active_jobs"] = row["c"] or 0
        row = session.run("MATCH (s:ServiceRequest) RETURN count(s) AS c").single()
        if row:
            data["active_services"] = row["c"] or 0

    return render_template("admin/reports.html", data=data)


