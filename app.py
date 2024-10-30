from flask import Flask, render_template
import sqlite3

app = Flask(__name__)
DATABASE = 'exchange.db'

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Enables dict-like access to rows
    return conn

# Homepage route
@app.route('/')
def index():
    conn = get_db_connection()
    # Example query, if you want to use data from the database
    # rows = conn.execute('SELECT * FROM some_table').fetchall()
    conn.close()
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
