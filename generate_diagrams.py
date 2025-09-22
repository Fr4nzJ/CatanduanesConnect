# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch
import numpy as np
import os
import textwrap

def draw_arrow(ax, start, end, color='black', lw=2, head_width=12, head_length=12):
    """Draw an arrow from the edge of one box to the edge of another."""
    arrow = FancyArrowPatch(start, end, arrowstyle='-|>', color=color, linewidth=lw,
                           mutation_scale=head_width, shrinkA=10, shrinkB=10)
    ax.add_patch(arrow)

def create_context_diagram():
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Main system
    system_xy = (4, 3)
    system_w, system_h = 4, 2
    system_center = (system_xy[0] + system_w/2, system_xy[1] + system_h/2)
    system = patches.Rectangle(system_xy, system_w, system_h, facecolor='lightblue', edgecolor='black')
    ax.add_patch(system)
    ax.text(*system_center, 'Catanduanes\nConnect', ha='center', va='center')
    
    # External entities
    entities = {
        'Users': (2, 6),
        'Google Maps API': (2, 2),
        'AI Chatbot': (10, 6),
        'Email Service': (10, 2),
        'Payment Gateway': (6, 1)
    }
    entity_w, entity_h = 2, 1
    for name, pos in entities.items():
        rect = patches.Rectangle(pos, entity_w, entity_h, facecolor='lightgreen', edgecolor='black')
        ax.add_patch(rect)
        center = (pos[0] + entity_w/2, pos[1] + entity_h/2)
        ax.text(*center, name, ha='center', va='center', fontsize=8)
        # Draw arrows from edge to edge
        # Calculate direction
        dx = system_center[0] - center[0]
        dy = system_center[1] - center[1]
        norm = np.hypot(dx, dy)
        # Start at edge of entity box
        start = (center[0] + (entity_w/2) * dx/norm, center[1] + (entity_h/2) * dy/norm)
        # End at edge of system box
        end = (system_center[0] - (system_w/2) * dx/norm, system_center[1] - (system_h/2) * dy/norm)
        draw_arrow(ax, start, end)
    
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')
    plt.savefig('static/images/context_diagram.png', bbox_inches='tight', dpi=300)
    plt.close()

def create_data_flow_diagram():
    fig, ax = plt.subplots(figsize=(12, 8))
    # Processes
    processes = {
        'User Registration': (2, 6),
        'Business Listing': (2, 4),
        'Job Posting': (2, 2),
        'AI Chatbot': (10, 4)
    }
    stores = {
        'Database': (6, 6),
        'Map Display': (6, 4),
        'Search Index': (6, 2)
    }
    box_w, box_h = 2, 1
    # Draw processes
    for name, pos in processes.items():
        rect = patches.Rectangle(pos, box_w, box_h, facecolor='lightblue', edgecolor='black')
        ax.add_patch(rect)
        center = (pos[0] + box_w/2, pos[1] + box_h/2)
        ax.text(*center, name, ha='center', va='center', fontsize=8)
    # Draw data stores
    for name, pos in stores.items():
        rect = patches.Rectangle(pos, box_w, box_h, facecolor='lightgreen', edgecolor='black')
        ax.add_patch(rect)
        center = (pos[0] + box_w/2, pos[1] + box_h/2)
        ax.text(*center, name, ha='center', va='center', fontsize=8)
    # Draw arrows
    # User Registration -> Database
    draw_arrow(ax, (4,6.5), (6,6.5))
    # Business Listing -> Map Display -> AI Chatbot
    draw_arrow(ax, (4,4.5), (6,4.5))
    draw_arrow(ax, (8,4.5), (10,4.5))
    # Job Posting -> Search Index
    draw_arrow(ax, (4,2.5), (6,2.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')
    plt.savefig('static/images/data_flow_diagram.png', bbox_inches='tight', dpi=300)
    plt.close()

def create_user_diagram():
    fig, ax = plt.subplots(figsize=(12, 8))
    roles = {
        'Job Seeker': (2, 6),
        'Business Owner': (2, 4),
        'Administrator': (2, 2),
        'System (AI Chatbot)': (10, 4)
    }
    features = {
        'Search Jobs': (6, 6),
        'Apply for Jobs': (6, 5),
        'Post Jobs': (6, 4),
        'Manage Business': (6, 3),
        'Admin Panel': (6, 2),
        'Chat Support': (6, 1)
    }
    box_w, box_h = 2, 1
    # Draw roles
    for name, pos in roles.items():
        rect = patches.Rectangle(pos, box_w, box_h, facecolor='lightblue', edgecolor='black')
        ax.add_patch(rect)
        center = (pos[0] + box_w/2, pos[1] + box_h/2)
        ax.text(*center, name, ha='center', va='center', fontsize=8)
    # Draw features
    for name, pos in features.items():
        rect = patches.Rectangle(pos, box_w, box_h, facecolor='lightgreen', edgecolor='black')
        ax.add_patch(rect)
        center = (pos[0] + box_w/2, pos[1] + box_h/2)
        ax.text(*center, name, ha='center', va='center', fontsize=8)
    # Draw arrows from roles to features
    draw_arrow(ax, (4,6.5), (6,6.5)) # Job Seeker -> Search Jobs
    draw_arrow(ax, (4,6.5), (6,5.5)) # Job Seeker -> Apply for Jobs
    draw_arrow(ax, (4,4.5), (6,4.5)) # Business Owner -> Post Jobs
    draw_arrow(ax, (4,4.5), (6,3.5)) # Business Owner -> Manage Business
    draw_arrow(ax, (4,2.5), (6,2.5)) # Administrator -> Admin Panel
    draw_arrow(ax, (4,2.5), (6,1.5)) # Administrator -> Chat Support
    draw_arrow(ax, (8,4.5), (10,4.5)) # Post Jobs -> System (AI Chatbot)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')
    plt.savefig('static/images/user_diagram.png', bbox_inches='tight', dpi=300)
    plt.close()

def create_activity_diagram():
    fig, ax = plt.subplots(figsize=(12, 8))
    lanes = {
        'Job Seeker': (2, 6),
        'System': (2, 4),
        'Business Owner': (2, 2)
    }
    activities = {
        'Search Jobs': (4, 6),
        'Submit Application': (6, 6),
        'Process Application': (6, 4),
        'Send Notification': (8, 4),
        'Review Application': (8, 2),
        'Post Job': (10, 2)
    }
    box_w, box_h = 2, 1
    # Draw lanes
    for name, pos in lanes.items():
        rect = patches.Rectangle(pos, box_w, box_h, facecolor='lightblue', edgecolor='black')
        ax.add_patch(rect)
        center = (pos[0] + box_w/2, pos[1] + box_h/2)
        ax.text(*center, name, ha='center', va='center', fontsize=8)
    # Draw activities
    for name, pos in activities.items():
        rect = patches.Rectangle(pos, box_w, box_h, facecolor='lightgreen', edgecolor='black')
        ax.add_patch(rect)
        center = (pos[0] + box_w/2, pos[1] + box_h/2)
        ax.text(*center, name, ha='center', va='center', fontsize=8)
    # Draw arrows between activities
    activity_keys = list(activities.keys())
    for i in range(len(activity_keys) - 1):
        start_name = activity_keys[i]
        end_name = activity_keys[i+1]
        start_pos = activities[start_name]
        end_pos = activities[end_name]
        start = (start_pos[0] + box_w, start_pos[1] + box_h/2)
        end = (end_pos[0], end_pos[1] + box_h/2)
        draw_arrow(ax, start, end)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')
    plt.savefig('static/images/activity_diagram.png', bbox_inches='tight', dpi=300)
    plt.close()

def create_er_diagram():
    fig, ax = plt.subplots(figsize=(12, 8))
    entities = {
        'User\n(id, name, email, role)': (2, 6),
        'Business\n(id, name, location, category)': (2, 4),
        'Job\n(id, title, description, salary)': (6, 4),
        'Application\n(id, status, cover_letter)': (6, 2),
        'Review\n(id, rating, comment)': (10, 4)
    }
    box_w, box_h = 2, 1
    centers = {}
    # Draw entities
    for name, pos in entities.items():
        rect = patches.Rectangle(pos, box_w, box_h, facecolor='lightblue', edgecolor='black')
        ax.add_patch(rect)
        center = (pos[0] + box_w/2, pos[1] + box_h/2)
        centers[name] = center
        ax.text(*center, name, ha='center', va='center', fontsize=8)
    # Draw relationships
    rels = [
        ('User\n(id, name, email, role)', 'Business\n(id, name, location, category)', 'owns'),
        ('Business\n(id, name, location, category)', 'Job\n(id, title, description, salary)', 'posts'),
        ('User\n(id, name, email, role)', 'Application\n(id, status, cover_letter)', 'submits'),
        ('Job\n(id, title, description, salary)', 'Application\n(id, status, cover_letter)', 'receives'),
        ('User\n(id, name, email, role)', 'Review\n(id, rating, comment)', 'writes'),
        ('Business\n(id, name, location, category)', 'Review\n(id, rating, comment)', 'receives')
    ]
    for start_name, end_name, label in rels:
        start = centers[start_name]
        end = centers[end_name]
        # Move start/end to edge of box
        dx, dy = end[0] - start[0], end[1] - start[1]
        norm = np.hypot(dx, dy)
        start_edge = (start[0] + (box_w/2) * dx/norm, start[1] + (box_h/2) * dy/norm)
        end_edge = (end[0] - (box_w/2) * dx/norm, end[1] - (box_h/2) * dy/norm)
        draw_arrow(ax, start_edge, end_edge)
        mid_x = (start_edge[0] + end_edge[0]) / 2
        mid_y = (start_edge[1] + end_edge[1]) / 2
        ax.text(mid_x, mid_y, label, ha='center', va='center', fontsize=8)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')
    plt.savefig('static/images/er_diagram.png', bbox_inches='tight', dpi=300)
    plt.close()

def create_system_architecture():
    fig, ax = plt.subplots(figsize=(12, 8))
    layers = [
        'Frontend\n(HTML5, CSS3, JavaScript, Bootstrap 5)',
        'Backend\n(Flask, Python)',
        'Database\n(PostgreSQL)',
        'AI Services\n(Hugging Face)',
        'Maps\n(Google Maps API, Leaflet.js)',
        'Deployment\n(Docker, AWS/GCP)'
    ]
    box_w, box_h = 8, 0.8
    y_start = 6
    for i, name in enumerate(layers):
        y = y_start - i
        rect = patches.Rectangle((2, y), box_w, box_h, facecolor='lightblue', edgecolor='black')
        ax.add_patch(rect)
        ax.text(2 + box_w/2, y + box_h/2, name, ha='center', va='center', fontsize=8)
        if i > 0:
            # Draw arrow from previous to current
            draw_arrow(ax, (2 + box_w/2, y + box_h + 0.01), (2 + box_w/2, y + box_h + 0.79))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')
    plt.savefig('static/images/system_architecture.png', bbox_inches='tight', dpi=300)
    plt.close()

def create_storyboard():
    fig, ax = plt.subplots(figsize=(12, 8))
    screens = {
        'Home Page': (2, 4),
        'Login': (4, 6),
        'Register': (4, 2),
        'Dashboard': (6, 4),
        'Interactive Map': (8, 6),
        'Chatbot': (8, 2)
    }
    box_w, box_h = 2, 1
    centers = {}
    for name, pos in screens.items():
        rect = patches.Rectangle(pos, box_w, box_h, facecolor='lightblue', edgecolor='black')
        ax.add_patch(rect)
        center = (pos[0] + box_w/2, pos[1] + box_h/2)
        centers[name] = center
        ax.text(*center, name, ha='center', va='center', fontsize=8)
    # Draw flow arrows
    flow = [
        ('Home Page', 'Login'),
        ('Home Page', 'Register'),
        ('Login', 'Dashboard'),
        ('Register', 'Dashboard'),
        ('Dashboard', 'Interactive Map'),
        ('Dashboard', 'Chatbot')
    ]
    for start_name, end_name in flow:
        start = centers[start_name]
        end = centers[end_name]
        dx, dy = end[0] - start[0], end[1] - start[1]
        norm = np.hypot(dx, dy)
        start_edge = (start[0] + (box_w/2) * dx/norm, start[1] + (box_h/2) * dy/norm)
        end_edge = (end[0] - (box_w/2) * dx/norm, end[1] - (box_h/2) * dy/norm)
        draw_arrow(ax, start_edge, end_edge)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')
    plt.savefig('static/images/storyboard.png', bbox_inches='tight', dpi=300)
    plt.close()

def create_conceptual_framework():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('off')
    # Box positions and sizes
    box_w, box_h = 3, 4
    y = 2
    input_x = 1
    process_x = 6
    output_x = 11
    # Draw maroon title bars
    bar_h = 0.5
    bar_color = '#a01b2f'
    ax.add_patch(patches.Rectangle((input_x, y + box_h), box_w, bar_h, facecolor=bar_color, edgecolor='none'))
    ax.add_patch(patches.Rectangle((process_x, y + box_h), box_w, bar_h, facecolor=bar_color, edgecolor='none'))
    ax.add_patch(patches.Rectangle((output_x, y + box_h), box_w, bar_h, facecolor=bar_color, edgecolor='none'))
    # Draw boxes
    input_box = patches.Rectangle((input_x, y), box_w, box_h, facecolor='white', edgecolor='black', linewidth=2)
    process_box = patches.Rectangle((process_x, y), box_w, box_h, facecolor='white', edgecolor='black', linewidth=2)
    output_box = patches.Rectangle((output_x, y), box_w, box_h, facecolor='white', edgecolor='black', linewidth=2)
    ax.add_patch(input_box)
    ax.add_patch(process_box)
    ax.add_patch(output_box)
    # Titles (on bars)
    ax.text(input_x + box_w/2, y + box_h + bar_h/2, 'INPUT', ha='center', va='center', fontsize=18, color='white', weight='bold')
    ax.text(process_x + box_w/2, y + box_h + bar_h/2, 'PROCESS', ha='center', va='center', fontsize=18, color='white', weight='bold')
    ax.text(output_x + box_w/2, y + box_h + bar_h/2, 'OUTPUT', ha='center', va='center', fontsize=18, color='white', weight='bold')
    # Helper for wrapped text
    def draw_bullets(ax, x, y_start, items, box_w, line_height=0.5, fontsize=13, wrap=28):
        y = y_start
        for item in items:
            lines = textwrap.wrap(item, width=wrap)
            for j, line in enumerate(lines):
                prefix = '\u2022 ' if j == 0 else '   '
                ax.text(x, y, prefix + line, ha='left', va='top', fontsize=fontsize)
                y -= line_height
    # Input items
    input_items = [
        'User registrations and profiles',
        'Business listings and details',
        'Job postings and applications',
        'Map/location data',
        'User queries (AI chatbot)',
        'External API data (Google Maps, payments)'
    ]
    draw_bullets(ax, input_x + 0.2, y + box_h - 0.5, input_items, box_w, line_height=0.5, fontsize=13, wrap=28)
    # Process items
    process_items = [
        'User authentication & management',
        'Business directory management',
        'Job portal operations',
        'Interactive map rendering',
        'AI chatbot processing',
        'Data storage & retrieval',
        'Security & validation',
        'Notification & feedback'
    ]
    draw_bullets(ax, process_x + 0.2, y + box_h - 0.5, process_items, box_w, line_height=0.5, fontsize=13, wrap=28)
    # Output highlight (move to top of output box)
    ax.text(output_x + box_w/2, y + box_h - 0.3, 'Functional and Evaluated\nCatanduanes Connect System', ha='center', va='top', fontsize=14, color='black', weight='bold')
    # Output items (move down)
    output_items = [
        'Functional Catanduanes Connect platform',
        'Searchable business directory',
        'Job matching & application results',
        'Interactive map with locations',
        'AI-powered user assistance',
        'User feedback & analytics'
    ]
    draw_bullets(ax, output_x + 0.2, y + box_h - 1.2, output_items, box_w, line_height=0.5, fontsize=13, wrap=28)
    # Arrows between boxes (avoid text overlap)
    draw_arrow(ax, (input_x + box_w + 0.05, y + box_h/2), (process_x - 0.05, y + box_h/2), lw=3, head_width=18)
    draw_arrow(ax, (process_x + box_w + 0.05, y + box_h/2), (output_x - 0.05, y + box_h/2), lw=3, head_width=18)
    # Feedback box and arrows
    feedback_y = y - 1.2
    feedback_w = 3
    feedback_h = 0.7
    feedback_x = process_x + box_w/2 - feedback_w/2
    feedback_box = patches.Rectangle((feedback_x, feedback_y), feedback_w, feedback_h, facecolor=bar_color, edgecolor='none')
    ax.add_patch(feedback_box)
    ax.text(feedback_x + feedback_w/2, feedback_y + feedback_h/2, 'FEEDBACK', ha='center', va='center', fontsize=16, color='white', weight='bold')
    # Feedback arrows (curved for clarity)
    ax.annotate('', xy=(output_x + box_w/2, y), xytext=(feedback_x + feedback_w, feedback_y + feedback_h),
                arrowprops=dict(arrowstyle='-|>', color='black', lw=2, connectionstyle='arc3,rad=-0.3', mutation_scale=14))
    ax.annotate('', xy=(feedback_x, feedback_y + feedback_h), xytext=(input_x + box_w/2, y),
                arrowprops=dict(arrowstyle='-|>', color='black', lw=2, connectionstyle='arc3,rad=-0.3', mutation_scale=14))
    plt.xlim(0, 15)
    plt.ylim(0, 8)
    plt.savefig('static/images/conceptual_framework.png', bbox_inches='tight', dpi=300)
    plt.close()

def main():
    create_context_diagram()
    create_data_flow_diagram()
    create_user_diagram()
    create_activity_diagram()
    create_er_diagram()
    create_system_architecture()
    create_storyboard()
    create_conceptual_framework()

if __name__ == '__main__':
    main() 