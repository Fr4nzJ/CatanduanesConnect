from flask_login import UserMixin
from datetime import datetime

class User(UserMixin):
    def __init__(self, id, email, name, role='client', is_verified=False, created_at=None):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.is_verified = is_verified
        self.created_at = created_at or datetime.utcnow()

    @staticmethod
    def from_db_record(record):
        """Create a User instance from a database record."""
        if not record:
            return None
        return User(
            id=record['id'],
            email=record['email'],
            name=record['name'],
            role=record.get('role', 'client'),
            is_verified=record.get('is_verified', False),
            created_at=record.get('created_at')
        )

class Business:
    def __init__(self, id, name, owner_id, description, category, location, latitude, longitude, 
                 logo_url=None, permits=None, created_at=None, verified=False):
        self.id = id
        self.name = name
        self.owner_id = owner_id
        self.description = description
        self.category = category
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.logo_url = logo_url
        self.permits = permits or []
        self.created_at = created_at or datetime.utcnow()
        self.verified = verified

    @staticmethod
    def from_db_record(record):
        """Create a Business instance from a database record."""
        if not record:
            return None
        return Business(
            id=record['id'],
            name=record['name'],
            owner_id=record['owner_id'],
            description=record['description'],
            category=record['category'],
            location=record['location'],
            latitude=record['latitude'],
            longitude=record['longitude'],
            logo_url=record.get('logo_url'),
            permits=record.get('permits', []),
            created_at=record.get('created_at'),
            verified=record.get('verified', False)
        )

class Job:
    def __init__(self, id, title, business_id, description, category, location, latitude, longitude,
                 salary=None, qualifications=None, status='open', created_at=None):
        self.id = id
        self.title = title
        self.business_id = business_id
        self.description = description
        self.category = category
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.salary = salary
        self.qualifications = qualifications or []
        self.status = status
        self.created_at = created_at or datetime.utcnow()

    @staticmethod
    def from_db_record(record):
        """Create a Job instance from a database record."""
        if not record:
            return None
        return Job(
            id=record['id'],
            title=record['title'],
            business_id=record['business_id'],
            description=record['description'],
            category=record['category'],
            location=record['location'],
            latitude=record['latitude'],
            longitude=record['longitude'],
            salary=record.get('salary'),
            qualifications=record.get('qualifications', []),
            status=record.get('status', 'open'),
            created_at=record.get('created_at')
        )

class Service:
    def __init__(self, id, title, requester_id, description, category, location, latitude, longitude,
                 budget=None, status='open', created_at=None):
        self.id = id
        self.title = title
        self.requester_id = requester_id
        self.description = description
        self.category = category
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.budget = budget
        self.status = status
        self.created_at = created_at or datetime.utcnow()

    @staticmethod
    def from_db_record(record):
        """Create a Service instance from a database record."""
        if not record:
            return None
        return Service(
            id=record['id'],
            title=record['title'],
            requester_id=record['requester_id'],
            description=record['description'],
            category=record['category'],
            location=record['location'],
            latitude=record['latitude'],
            longitude=record['longitude'],
            budget=record.get('budget'),
            status=record.get('status', 'open'),
            created_at=record.get('created_at')
        )

class Application:
    def __init__(self, id, user_id, job_id, cover_letter=None, resume_url=None, status='pending',
                 created_at=None):
        self.id = id
        self.user_id = user_id
        self.job_id = job_id
        self.cover_letter = cover_letter
        self.resume_url = resume_url
        self.status = status
        self.created_at = created_at or datetime.utcnow()

    @staticmethod
    def from_db_record(record):
        """Create an Application instance from a database record."""
        if not record:
            return None
        return Application(
            id=record['id'],
            user_id=record['user_id'],
            job_id=record['job_id'],
            cover_letter=record.get('cover_letter'),
            resume_url=record.get('resume_url'),
            status=record.get('status', 'pending'),
            created_at=record.get('created_at')
        )

class Notification:
    def __init__(self, id, user_id, title, message, type='info', read=False, created_at=None):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.message = message
        self.type = type
        self.read = read
        self.created_at = created_at or datetime.utcnow()

    @staticmethod
    def from_db_record(record):
        """Create a Notification instance from a database record."""
        if not record:
            return None
        return Notification(
            id=record['id'],
            user_id=record['user_id'],
            title=record['title'],
            message=record['message'],
            type=record.get('type', 'info'),
            read=record.get('read', False),
            created_at=record.get('created_at')
        )

class Review:
    def __init__(self, id, reviewer_id, target_id, target_type, rating, comment=None, created_at=None):
        self.id = id
        self.reviewer_id = reviewer_id
        self.target_id = target_id  # Can be business_id, service_id, etc.
        self.target_type = target_type  # 'business', 'service', etc.
        self.rating = rating  # 1-5 stars
        self.comment = comment
        self.created_at = created_at or datetime.utcnow()

    @staticmethod
    def from_db_record(record):
        """Create a Review instance from a database record."""
        if not record:
            return None
        return Review(
            id=record['id'],
            reviewer_id=record['reviewer_id'],
            target_id=record['target_id'],
            target_type=record['target_type'],
            rating=record['rating'],
            comment=record.get('comment'),
            created_at=record.get('created_at')
        )

class Activity:
    def __init__(self, id, user_id, action_type, target_id=None, target_type=None, 
                 data=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.action_type = action_type  # 'login', 'job_post', 'service_request', etc.
        self.target_id = target_id
        self.target_type = target_type
        self.data = data or {}  # Additional activity data
        self.created_at = created_at or datetime.utcnow()

    @staticmethod
    def from_db_record(record):
        """Create an Activity instance from a database record."""
        if not record:
            return None
        return Activity(
            id=record['id'],
            user_id=record['user_id'],
            action_type=record['action_type'],
            target_id=record.get('target_id'),
            target_type=record.get('target_type'),
            data=record.get('data', {}),
            created_at=record.get('created_at')
        )