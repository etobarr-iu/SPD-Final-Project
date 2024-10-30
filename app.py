from flask import Flask, render_template, url_for, redirect, request

app = Flask(__name__)

# Dummy data for resources and events
resources = [
    {"id": 1, "name": "Lawn Mower", "description": "Electric lawn mower for medium-sized lawns."},
    {"id": 2, "name": "Ladder", "description": "10-foot ladder, suitable for outdoor use."}
]

events = [
    {"name": "Gardening Workshop", "description": "Learn about sustainable gardening techniques.", "date": "2024-11-01"},
    {"name": "Community Cleanup", "description": "Join us in cleaning up the neighborhood park.", "date": "2024-11-15"}
]

# Dummy data for a sample user profile
user = {
    "name": "John Doe",
    "reputation": 4.8,
    "resources": resources,
    "reservations": [
        {"resource_name": "Lawn Mower", "date": "2024-11-05"},
        {"resource_name": "Ladder", "date": "2024-11-10"}
    ]
}

# Home page route
@app.route('/')
def home():
    return render_template('home.html')

# Resource listing page route
@app.route('/resources')
def resources_list():
    return render_template('resources.html', resources=resources)

# Resource detail page route (dynamic route to display a single resource)
@app.route('/resources/<int:resource_id>')
def resource_detail(resource_id):
    # Find the resource by id
    resource = next((item for item in resources if item["id"] == resource_id), None)
    if resource:
        return render_template('resource_detail.html', resource=resource)
    return "Resource not found", 404

# Reservation route (handles POST request for reserving a resource)
@app.route('/resources/<int:resource_id>/reserve', methods=['POST'])
def reserve_resource(resource_id):
    # Find the resource by id
    resource = next((item for item in resources if item["id"] == resource_id), None)
    if resource:
        reserved_date = request.form['date']
        # Simulate storing the reservation (actual logic would save to a database)
        return redirect(url_for('resources_list'))
    return "Resource not found", 404

# Community events page route
@app.route('/events')
def events_list():
    return render_template('events.html', events=events)

# User profile page route
@app.route('/profile')
def profile():
    return render_template('profile.html', user=user)

if __name__ == '__main__':
    app.run(debug=True)
