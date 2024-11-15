from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'blah_blah_secret_whatever'  # Change this to a secure random key

# Helper function to connect to the database
def get_db_connection():
    conn = sqlite3.connect('exchange.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/registration')
def registration():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    profile_image = request.form.get('profile_image', '')
    location = request.form.get('location', '')

    if not name or not email or not password:
        flash('Name, email, and password are required', 'error')
        return redirect(url_for('registration'))

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO Users (name, email, password, profile_image, location) VALUES (?, ?, ?, ?, ?)",
            (name, email, password, profile_image, location)
        )
        conn.commit()
        flash('Registration successful', 'success')
    except sqlite3.IntegrityError:
        flash('Email already registered', 'error')
    finally:
        conn.close()

    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('login'))

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM Users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user is None or user['password'] != password:
            flash('Invalid email or password', 'error')
        else:
            session['user_id'] = user['user_id']
            flash('Login successful', 'success')
            return redirect(url_for('profile'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/')
@app.route('/index')
def index():
    conn = get_db_connection()

    # Recent listings query remains the same
    recent_listings = conn.execute('''
        SELECT Resources.*, Users.name AS user_name, Users.profile_image
        FROM Resources
        JOIN Users ON Resources.user_id = Users.user_id
        ORDER BY date_posted DESC
        LIMIT 5
    ''').fetchall()

    # Top-rated users query now includes profile_image
    top_rated_users = conn.execute('''
        SELECT Users.user_id, Users.name, Users.profile_image, AVG(Reviews.rating) AS average_rating
        FROM Reviews
        JOIN Users ON Reviews.user_id = Users.user_id
        GROUP BY Users.user_id
        HAVING COUNT(Reviews.rating) >= 1
        ORDER BY average_rating DESC
        LIMIT 5
    ''').fetchall()

    conn.close()
    return render_template('homepage.html', recent_listings=recent_listings, top_rated_users=top_rated_users)

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if user_id is None:
        flash('Please log in to access your profile', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM Users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()

    return render_template('profile.html', 
                           user_name=user['name'], 
                           user_email=user['email'], 
                           user_location=user['location'],
                           user_profile_image=user['profile_image'])

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please log in to access your profile', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()

    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        email = request.form['email']
        location = request.form.get('location', '')
        profile_image = request.form.get('profile_image', '')

        # Update the user's profile information
        conn.execute('''
            UPDATE Users 
            SET name = ?, email = ?, location = ?, profile_image = ? 
            WHERE user_id = ?
        ''', (name, email, location, profile_image, user_id))
        conn.commit()
        conn.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    # GET request: Retrieve the current user information to pre-fill the form
    user = conn.execute('SELECT * FROM Users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()

    return render_template('edit_profile.html', 
                           user_name=user['name'], 
                           user_email=user['email'], 
                           user_location=user['location'], 
                           user_profile_image=user['profile_image'])



@app.route('/resources', methods=['GET'])
def resources():
    # Get search filters from the request
    category = request.args.get('category', '').strip()
    keywords = request.args.get('keywords', '').strip()
    location = request.args.get('location', '').strip()

    # Build the query with optional filters
    query = '''
        SELECT Resources.*, Users.name AS user_name, Users.location AS user_location
        FROM Resources
        JOIN Users ON Resources.user_id = Users.user_id
        WHERE 1 = 1
    '''
    params = []

    if category:
        query += " AND Resources.category LIKE ?"
        params.append(f"%{category}%")
    if keywords:
        query += " AND (Resources.title LIKE ? OR Resources.description LIKE ?)"
        params.extend([f"%{keywords}%", f"%{keywords}%"])
    if location:
        query += " AND Users.location LIKE ?"
        params.append(f"%{location}%")

    # Execute the query
    conn = get_db_connection()
    resources = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('resources.html', resources=resources)



@app.route('/my_resources', methods=['GET', 'POST'])
def my_resources():
    if 'user_id' not in session:
        flash('Please log in to access your resources', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        # Adding a new resource
        title = request.form['title']
        description = request.form.get('description', '')
        category = request.form['category']
        availability = request.form.get('availability', 'available')
        images = request.form.get('images', '')  # New field for image path
        user_id = session['user_id']
        
        conn.execute(
            'INSERT INTO Resources (user_id, title, description, category, availability, images, date_posted) VALUES (?, ?, ?, ?, ?, ?, datetime("now"))',
            (user_id, title, description, category, availability, images)
        )
        conn.commit()
        flash('Resource added successfully!', 'success')

    # Retrieve all resources created by the logged-in user
    my_resources = conn.execute('''
        SELECT * FROM Resources WHERE user_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('my_resources.html', resources=my_resources)

@app.route('/edit_resource/<int:resource_id>', methods=['GET', 'POST'])
def edit_resource(resource_id):
    conn = get_db_connection()
    resource = conn.execute('SELECT * FROM Resources WHERE resource_id = ? AND user_id = ?', 
                            (resource_id, session['user_id'])).fetchone()

    if not resource:
        flash('Resource not found or you do not have permission to edit it.', 'error')
        return redirect(url_for('my_resources'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        category = request.form['category']
        availability = request.form['availability']
        conn.execute(
            'UPDATE Resources SET title = ?, description = ?, category = ?, availability = ? WHERE resource_id = ?',
            (title, description, category, availability, resource_id)
        )
        conn.commit()
        flash('Resource updated successfully!', 'success')
        return redirect(url_for('my_resources'))

    conn.close()
    return render_template('edit_resource.html', resource=resource)

@app.route('/delete_resource/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM Resources WHERE resource_id = ? AND user_id = ?', (resource_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Resource deleted successfully', 'success')
    return redirect(url_for('my_resources'))

@app.route('/messages', methods=['GET', 'POST'])
def messages():
    if 'user_id' not in session:
        flash('Please log in to access your messages', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        # Sending a new message
        receiver_id = request.form['receiver_id']
        content = request.form['content']
        conn.execute(
            'INSERT INTO Messages (sender_id, receiver_id, content, timestamp) VALUES (?, ?, ?, datetime("now"))',
            (session['user_id'], receiver_id, content)
        )
        conn.commit()
        flash('Message sent!', 'success')

    # Retrieve optional resource_id for prepopulating the message box
    resource_id = request.args.get('resource_id')
    prepopulated_message = ""
    prepopulated_receiver = None
    if resource_id:
        resource = conn.execute(
            'SELECT title, user_id FROM Resources WHERE resource_id = ?',
            (resource_id,)
        ).fetchone()
        if resource:
            prepopulated_message = f"I am interested in your {resource['title']}"
            prepopulated_receiver = resource['user_id']

    # Retrieve all messages for display
    all_messages = conn.execute(
        '''SELECT Messages.*, sender.name AS sender_name, receiver.name AS receiver_name, sender.profile_image AS sender_image
           FROM Messages
           JOIN Users AS sender ON Messages.sender_id = sender.user_id
           JOIN Users AS receiver ON Messages.receiver_id = receiver.user_id
           WHERE Messages.sender_id = ? OR Messages.receiver_id = ?
           ORDER BY Messages.timestamp DESC''',
        (session['user_id'], session['user_id'])
    ).fetchall()

    # Fetch all users for the dropdown
    users = conn.execute('SELECT user_id, name FROM Users WHERE user_id != ?', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('messages.html', all_messages=all_messages, users=users, prepopulated_message=prepopulated_message, prepopulated_receiver=prepopulated_receiver)




@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if 'user_id' not in session:
        flash('Please log in to access your reviews', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        # Submitting a new review
        user_id = request.form['user_id']
        rating = request.form['rating']
        comment = request.form.get('comment', '')
        conn.execute(
            'INSERT INTO Reviews (user_id, reviewer_id, rating, comment, timestamp) VALUES (?, ?, ?, ?, datetime("now"))',
            (user_id, session['user_id'], rating, comment)
        )
        conn.commit()
        flash('Review submitted successfully!', 'success')

    # Retrieve all reviews received by the logged-in user
    reviews = conn.execute(
        'SELECT Reviews.*, reviewer.name AS reviewer_name, reviewer.profile_image AS reviewer_image '
        'FROM Reviews '
        'JOIN Users AS reviewer ON Reviews.reviewer_id = reviewer.user_id '
        'WHERE Reviews.user_id = ?',
        (session['user_id'],)
    ).fetchall()

    # Fetch all users for the dropdown, excluding the current user
    users = conn.execute(
        'SELECT user_id, name FROM Users WHERE user_id != ?',
        (session['user_id'],)
    ).fetchall()

    conn.close()
    return render_template('reviews.html', reviews=reviews, users=users)



if __name__ == '__main__':
    app.run(debug=True)
