from config import SECRET_KEY
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_mysqldb import MySQL
import bcrypt
from datetime import timedelta

app = Flask(__name__)
app.config.from_pyfile('config.py')

# MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Rithika.m27'
app.config['MYSQL_DB'] = 'main'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  # To return query results as dictionaries

mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')
from flask import jsonify, request, session, render_template, redirect, url_for
import bcrypt
from flask_mysqldb import MySQL

@app.route('/register', methods=['GET', 'POST'])

def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        email = request.form['email']

        # Hash the password
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

        try:
            # Store username, hashed password, and email in the database
            cursor = mysql.connection.cursor()
            cursor.execute('INSERT INTO users (username, password, email) VALUES (%s, %s, %s)', 
                           (username, hashed_password, email))
            mysql.connection.commit()
            cursor.close()

            # Automatically log the user in after registration
            session['logged_in'] = True
            session['email'] = email

            # Send success response as JSON for AJAX handling
            return jsonify(success=True)
        
        except Exception as e:
            # Handle any database errors
            print(f"Error occurred: {e}")
            return jsonify(success=False, message="Registration failed. Please try again.")
    
    # For GET requests, render the registration page
    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'].encode('utf-8')

        # Retrieve the hashed password from the database for the given email
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.checkpw(password, user['password'].encode('utf-8')):
            # If passwords match, set the user as logged in
            session['logged_in'] = True
            session['email'] = email
            return redirect(url_for('mapping'))

        # If login fails, show an error message
        error = 'Invalid email or password. Please try again.'
        return render_template('login.html', error=error)
    
    return render_template('login.html')

@app.route('/track_bus/<int:bus_id>', methods=['GET'])
def track_bus(bus_id):
    try:
        cursor = mysql.connection.cursor()  # Correctly reference the MySQL cursor

        # SQL query to get the latest bus location data based on bus_id
        cursor.execute('''SELECT latitude, longitude, status, current_location, expected_arrival_time, actual_arrival_time, timestamp 
                          FROM bus_tracking 
                          WHERE bus_id = %s 
                          ORDER BY timestamp DESC LIMIT 1''', (bus_id,))
        location = cursor.fetchone()
        cursor.close()

        # If location data exists, pass it to the template
        if location:
            location_data = {
                'latitude': location['latitude'],
                'longitude': location['longitude'],
                'status': location['status'],
                'current_location': location['current_location'],
                'expected_arrival_time': location['expected_arrival_time'],
                'actual_arrival_time': location['actual_arrival_time'],
                'timestamp': location['timestamp']
            }
            return render_template('track_bus.html', location=location_data, bus_id=bus_id)
        else:
            # If no data, return an error message
            return render_template('track_bus.html', error='No location data available for this bus.', bus_id=bus_id)
    
    except Exception as e:
        # Log error and return an error message in case of issues
        print(f"Error retrieving bus data: {str(e)}")
        return render_template('track_bus.html', error='An error occurred while retrieving bus data.', bus_id=bus_id)

@app.route('/bus_routes', methods=['GET'])
def bus_routes():
    start_location = request.args.get('startLocation')
    end_location = request.args.get('endLocation')

    if start_location and end_location:
        try:
            cursor = mysql.connection.cursor()
            query = "SELECT * FROM bus_routes WHERE start_location=%s AND end_location=%s"
            cursor.execute(query, (start_location, end_location))
            bus_routes = cursor.fetchall()
            cursor.close()

            if not bus_routes:
                return render_template('bus_routes.html', bus_routes=[], error="No routes found.")

            return render_template('bus_routes.html', bus_routes=bus_routes)
        except Exception as e:
            return render_template('bus_routes.html', bus_routes=[], error=f"Error retrieving data: {str(e)}")

    return render_template('bus_routes.html', bus_routes=[], error="Please provide both start and end locations.")

@app.route('/bus_timing/<int:bus_id>', methods=['GET'])
def bus_timing(bus_id):
    try:
        cursor = mysql.connection.cursor()
        query = "SELECT * FROM bus_timings WHERE bus_id = %s"
        cursor.execute(query, (bus_id,))
        bus_timings = cursor.fetchall()
        cursor.close()

        if not bus_timings:
            return render_template('bus_timing.html', bus_timings=[], error="No timings found for this bus.")

        formatted_timings = []
        for timing in bus_timings:
            total_seconds = int(timing['timing'].total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"
            formatted_timings.append({'id': timing['id'], 'bus_id': timing['bus_id'], 'timing': formatted_time})

        return render_template('bus_timing.html', bus_timings=formatted_timings)
    except Exception as e:
        return render_template('bus_timing.html', bus_timings=[], error=f"Error retrieving data: {str(e)}")

@app.route('/mapping', methods=['GET', 'POST'])
def mapping():
    if session.get('logged_in'):
        if request.method == 'POST' and 'enable_location' in request.form:
            return render_template('location.html')
        return render_template('mapping.html')
    else:
        return redirect(url_for('login'))

@app.route('/location')
def location():
    return render_template('location.html')

@app.route('/combine', methods=['GET', 'POST'])
def combine():
    return render_template('combine.html')

@app.route('/all_bus_routes')
def all_bus_routes():
    return render_template('bus_routes.html')

@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.get_json()
    bus_id = data['bus_id']
    latitude = data['latitude']
    longitude = data['longitude']

    # Update the location in the database
    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE bus_tracking SET latitude = %s, longitude = %s, timestamp = NOW() WHERE bus_id = %s', 
                   (latitude, longitude, bus_id))
    mysql.connection.commit()
    cursor.close()

    return jsonify({"status": "success"}), 200

@app.route('/driver_tracking/<int:bus_id>', methods=['GET'])
def driver_tracking(bus_id):
    return render_template('driver_tracking.html', bus_id=bus_id)

if __name__ == '__main__':
    app.config['SECRET_KEY'] = 'xyz1234nbg789ty8inmcv2134'
    app.run(debug=True)
