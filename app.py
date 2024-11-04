from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure random key

# Helper function to connect to the database
def get_db_connection():
    conn = sqlite3.connect('exchange.db')
    conn.row_factory = sqlite3.Row
    return conn

# Authentication and Registration
@app.route('/registration')
@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    if not name or not email or not password:
        flash('Name, email, and password are required', 'error')
        return redirect(url_for('registration'))

    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO Users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        flash('Registration successful', 'success')
    except sqlite3.IntegrityError:
        flash('Email already registered', 'error')
    finally:
        conn.close()

    return redirect(url_for('registration'))

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

# Homepage
@app.route('/')
@app.route('/index')
def index():
    conn = get_db_connection()

    recent_listings = conn.execute('''
        SELECT Resources.*, Users.name AS user_name
        FROM Resources
        JOIN Users ON Resources.user_id = Users.user_id
        ORDER BY date_posted DESC
        LIMIT 5
    ''').fetchall()

    top_rated_users = conn.execute('''
        SELECT Users.user_id, Users.name, AVG(Reviews.rating) AS average_rating
        FROM Reviews
        JOIN Users ON Reviews.user_id = Users.user_id
        GROUP BY Users.user_id
        HAVING COUNT(Reviews.rating) >= 1
        ORDER BY average_rating DESC
        LIMIT 5
    ''').fetchall()

    conn.close()
    return render_template('homepage.html', recent_listings=recent_listings, top_rated_users=top_rated_users)

# User Profile
@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if user_id is None:
        flash('Please log in to access your profile', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM Users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()

    return render_template('profile.html', user_name=user['name'], user_id=user_id)

# Resources
@app.route('/resources')
def resources():
    conn = get_db_connection()
    resources = conn.execute('''
        SELECT Resources.*, Users.name AS user_name
        FROM Resources
        JOIN Users ON Resources.user_id = Users.user_id
    ''').fetchall()
    conn.close()
    return render_template('resources.html', resources=resources)

@app.route('/my_resources', methods=['GET', 'POST'])
def my_resources():
    if 'user_id' not in session:
        flash('Please log in to access your resources', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        category = request.form['category']
        availability = request.form.get('availability', 'available')
        user_id = session['user_id']
        conn.execute(
            'INSERT INTO Resources (user_id, title, description, category, availability, date_posted) VALUES (?, ?, ?, ?, ?, datetime("now"))',
            (user_id, title, description, category, availability)
        )
        conn.commit()
        flash('Resource added successfully!', 'success')

    my_resources = conn.execute('SELECT * FROM Resources WHERE user_id = ?', (session['user_id'],)).fetchall()
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

# Messages
@app.route('/messages', methods=['GET', 'POST'])
def messages():
    if 'user_id' not in session:
        flash('Please log in to access your messages', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        receiver_id = request.form['receiver_id']
        content = request.form['content']
        conn.execute(
            'INSERT INTO Messages (sender_id, receiver_id, content, timestamp) VALUES (?, ?, ?, datetime("now"))',
            (session['user_id'], receiver_id, content)
        )
        conn.commit()
        flash('Message sent!', 'success')

    inbox_messages = conn.execute('''
        SELECT Messages.*, sender.name AS sender_name, receiver.name AS receiver_name
        FROM Messages
        JOIN Users AS sender ON Messages.sender_id = sender.user_id
        JOIN Users AS receiver ON Messages.receiver_id = receiver.user_id
        WHERE Messages.receiver_id = ?
    ''', (session['user_id'],)).fetchall()

    sent_messages = conn.execute('''
        SELECT Messages.*, sender.name AS sender_name, receiver.name AS receiver_name
        FROM Messages
        JOIN Users AS sender ON Messages.sender_id = sender.user_id
        JOIN Users AS receiver ON Messages.receiver_id = receiver.user_id
        WHERE Messages.sender_id = ?
    ''', (session['user_id'],)).fetchall()

    users = conn.execute('SELECT user_id, name FROM Users WHERE user_id != ?', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('messages.html', inbox_messages=inbox_messages, sent_messages=sent_messages, users=users)

# Reviews
@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if 'user_id' not in session:
        flash('Please log in to access your reviews', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        user_id = request.form['user_id']
        rating = request.form['rating']
        comment = request.form.get('comment', '')
        conn.execute(
            'INSERT INTO Reviews (user_id, reviewer_id, rating, comment, timestamp) VALUES (?, ?, ?, ?, datetime("now"))',
            (user_id, session['user_id'], rating, comment)
        )
        conn.commit()
        flash('Review submitted successfully!', 'success')

    reviews = conn.execute(
        'SELECT Reviews.*, reviewer.name AS reviewer_name '
        'FROM Reviews '
        'JOIN Users AS reviewer ON Reviews.reviewer_id = reviewer.user_id '
        'WHERE Reviews.user_id = ?',
        (session['user_id'],)
    ).fetchall()
    conn.close()

    return render_template('reviews.html', reviews=reviews)

if __name__ == '__main__':
    app.run(debug=True)
