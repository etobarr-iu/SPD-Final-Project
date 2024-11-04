from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure random key

# Helper function to connect to the database
def get_db_connection():
    conn = sqlite3.connect('exchange.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/registration')
def index():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    if not name or not email or not password:
        flash('Name, email, and password are required', 'error')
        return redirect(url_for('index'))

    conn = sqlite3.connect('exchange.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO Users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
        conn.commit()
        flash('Registration successful', 'success')
    except sqlite3.IntegrityError:
        flash('Email already registered', 'error')
    finally:
        conn.close()

    return redirect(url_for('index'))

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('login'))

        conn = sqlite3.connect('exchange.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user is None or user[3] != password:  # Index 3 corresponds to 'password'
            flash('Invalid email or password', 'error')
        else:
            session['user_id'] = user[0]  # Index 0 corresponds to 'user_id'
            flash('Login successful', 'success')
            return redirect(url_for('profile'))

    return render_template('login.html')

@app.route('/profile')
def profile():
    user_id = session.get('user_id')
    if user_id is None:
        flash('Please log in to access your profile', 'error')
        return redirect(url_for('login'))

    conn = sqlite3.connect('exchange.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    user_name = user['name']

    return render_template('profile.html', user_name=user_name, user_id=user_id)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

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

# Route to display and manage the user's own resources
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
        user_id = session['user_id']
        conn.execute(
            'INSERT INTO Resources (user_id, title, description, category, availability, date_posted) VALUES (?, ?, ?, ?, ?, datetime("now"))',
            (user_id, title, description, category, availability)
        )
        conn.commit()
        flash('Resource added successfully!', 'success')

    # Retrieve all resources created by the logged-in user
    my_resources = conn.execute('''
        SELECT * FROM Resources WHERE user_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('my_resources.html', resources=my_resources)

# Route to edit a resource
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
        conn.close()
        flash('Resource updated successfully!', 'success')
        return redirect(url_for('my_resources'))

    conn.close()
    return render_template('edit_resource.html', resource=resource)

# Route to delete a resource
@app.route('/delete_resource/<int:resource_id>', methods=['POST'])
def delete_resource(resource_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM Resources WHERE resource_id = ? AND user_id = ?', 
                 (resource_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Resource deleted successfully!', 'success')
    return redirect(url_for('my_resources'))

# Route to display and send messages
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

    # Retrieve all messages involving the current user, including names
    messages = conn.execute('''
        SELECT Messages.*, 
               sender.name AS sender_name, 
               receiver.name AS receiver_name
        FROM Messages
        JOIN Users AS sender ON Messages.sender_id = sender.user_id
        JOIN Users AS receiver ON Messages.receiver_id = receiver.user_id
        WHERE receiver_id = ? OR sender_id = ?
    ''', (session['user_id'], session['user_id'])).fetchall()
    conn.close()

    return render_template('messages.html', messages=messages)

# Route to view and submit reviews
@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
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
        'SELECT * FROM Reviews WHERE user_id = ?', 
        (session['user_id'],)
    ).fetchall()
    conn.close()

    return render_template('reviews.html', reviews=reviews)

if __name__ == '__main__':
    app.run(debug=True)
