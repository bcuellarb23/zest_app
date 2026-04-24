import os
import bcrypt
import requests
import mysql.connector
from mysql.connector import pooling
from datetime import date, timedelta
from flask import Flask, render_template, request, jsonify, session, g
from flask_cors import CORS
from utils import calculate_nutritional_data
from dotenv import load_dotenv

load_dotenv()

# Configuration
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') # Cors configuration to allow cookies to be sent in cross-origin requests, necessary for session management between frontend and backend on different ports during development

# Environment Detection
IS_RENDER = os.environ.get('RENDER') == 'true'
DB_PORT = int(os.environ.get('DB_PORT'))

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME', 'food_tracker'),
    'port': DB_PORT
}

CA_PATH = "/etc/secrets/ca.pem" if IS_RENDER else "ca.pem"

pool_kwargs = {
    'pool_name': "hungry_pool",
    'pool_size': 3,
    **{k: v for k, v in DB_CONFIG.items() if v is not None}
}

if IS_RENDER or DB_CONFIG['host'] != 'localhost':
    pool_kwargs['ssl_ca'] = CA_PATH
    pool_kwargs['ssl_verify_cert'] = True
else:
    pool_kwargs['ssl_disabled'] = True

try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(**pool_kwargs)
    print("Successfully created connection pool!")

except mysql.connector.Error as err:
    raise Exception(f"DATABASE CONNECTION FAILED: {err}")

# Persistent session for external API calls to reuse TCP connections
http_session = requests.Session()

# New API Configuration
NEW_API_URL = os.environ.get('NEW_API_URL')
NEW_API_KEY = os.environ.get('NEW_API_KEY')

# Middleware and security 
origins = os.environ.get('ALLOWED_ORIGINS', '').split(',')
CORS(app, supports_credentials=True, origins=origins)

app.config.update(
    SESSION_COOKIE_SAMESITE='Lax', # Necessary for cookies to work in modern browsers on localhost
    SESSION_COOKIE_SECURE=True,    # Set to True because we are using HTTPS
    SESSION_COOKIE_HTTPONLY=True,  # Prevents JavaScript from reading the cookie (Security)
    PERMANENT_SESSION_LIFETIME=timedelta(days=7) # Keeps the session open for 15 minutes
)

# Routes definition
@app.route('/')
def index():
    return render_template('index.html', page_name="Index")

@app.route('/home')
def home():
    return render_template('home.html', page_name="home")

@app.route('/login')
def login():
    return render_template('login.html', page_name="Login")

@app.route('/signup')
def signup():
    return render_template('signup.html', page_name="signup")

@app.route('/add_food')
def add_food():
    return render_template('add_food.html', page_name="Add Food")

@app.route('/profile')
def profile():
    return render_template('profile.html', page_name="Profile")


# Image route
@app.context_processor
def inject_paths():
    return dict(img_path='/static/images/')

# Data base request
@app.before_request
def get_db():
    # Only establish a DB connection for API routes to save resources.
    # This prevents connecting to the DB just to serve CSS, JS, or HTML templates.
    if not request.path.startswith('/api'):
        return

    if 'db' not in g:
        try:
            g.db = db_pool.get_connection()
        except mysql.connector.Error as err:
            app.logger.error(f"Failed to connect to Database: {err}")
            return jsonify({"status": "error", "message": "Database connection failed"}), 500

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()


@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required"}), 400

    
    try:
        db = g.db
        with db.cursor(dictionary=True) as cursor: # returns a dictionary instead of a tuple
            # Fetch the user's ID and password hash from the database
            sql = "SELECT user_id, password_hash FROM login WHERE email = %s"
            cursor.execute(sql, (email,))
            user = cursor.fetchone()
            
        # Check if the user exists and the password is correct
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # Login successful. Store the user_id in the session
            session.permanent = True
            session['user_id'] = user['user_id']
            session['user_email'] = email
            return jsonify({"status": "success", "message": "Login successful"}), 200
        else:
            # User does not exist or password was incorrect
            return jsonify({"status": "error", "message": "Invalid email or password"}), 401
        
    except mysql.connector.Error as err:
        app.logger.error(f"database error during login for {email}: {err}")
        return jsonify({"status": "error", "message": "Database error occurred"}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error has occurred: {e}")
        return jsonify({"status": "error", "message": "An unexpected error occurred"}), 500

@app.route('/api/get_info')
def get_user_info():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "User not logged in"}), 401
    
    user_id = session['user_id']
           
    try:
        db = g.db
        with db.cursor(dictionary=True) as cursor:
            # Fetch basic info and the latest metrics history
            sql = """
                SELECT u.name, u.age, u.weight, u.height, h.goals, h.activity 
                FROM users u
                LEFT JOIN user_metrics_history h ON u.id = h.user_id
                WHERE u.id = %s
                ORDER BY h.updated_at DESC LIMIT 1
            """
            cursor.execute(sql, (user_id,))
            user_data = cursor.fetchone()

        if user_data:
            return jsonify({
                "status": "success", 
                "user_name": user_data['name'],
                "age": user_data['age'],
                "weight": user_data['weight'],
                "height": user_data['height'],
                "goals": user_data['goals'],
                "activity": user_data['activity']
            }), 200
        else:
            return jsonify({"status": "error", "message": "User not found"}), 404
    
    except mysql.connector.Error as err:
        #use a proper logging
        app.logger.error(f"database error fetching user info for user_id {user_id}: {err}")
        return jsonify({"status": "error", "message": "Database error occurred"}), 500


def get_food_by_name(food_item_name):
    # Makes a request to the Food API to search for products by name
    api_url = f"{NEW_API_URL}/foods/search"
    
    params = {
        'api_key': NEW_API_KEY,
        'query': food_item_name,
        'pageSize': 10  # Limit results for better performance
    }

    try:
        response = http_session.get(api_url, params=params, timeout=5)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return None
    
@app.route('/api/search_food', methods=['GET'])
def track_food():
    # Use request.args.get() to get the food_item from the URL query parameters
    food_item = request.args.get('food_item')

    if not food_item:
        return jsonify({"error": "Missing 'food_item' query parameter"}), 400

    # Call the helper function to get data from the API
    food_data = get_food_by_name(food_item)

    if food_data and 'foods' in food_data and food_data['foods']:
        simplified_food_list = []
        for product in food_data['foods']:
            # USDA returns nutrients in a list; we need to extract the ones we want by ID or Name
            nutrients = product.get('foodNutrients', [])
            
            def get_nutrient_value(nutrient_id):
                # Common USDA Nutrient IDs: 1008=Calories, 1003=Protein, 1005=Carbs, 1004=Fat
                for n in nutrients:
                    if n.get('nutrientId') == nutrient_id:
                        return n.get('value', 0)
                return 0

            if nutrients:
                simplified_data = {
                    'product_name': product.get('description', 'N/A'),
                    'proteins': get_nutrient_value(1003),
                    'calories': get_nutrient_value(1008),
                    'fat': get_nutrient_value(1004),
                    'carbohydrates': get_nutrient_value(1005),
                    'sugars': get_nutrient_value(2000), # 2000 is often Total Sugars
                }
                simplified_food_list.append(simplified_data)

        return jsonify(simplified_food_list)
   
    else:
        return jsonify({"message": f"No food found for '{food_item}'"}), 404
    

@app.route('/api/get-tdee', methods=['GET'])
def get_user_tdee():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "User not logged in"}), 401

    try:
        user_id = session['user_id']
        db = g.db
        with db.cursor(dictionary=True) as cursor:
            # Fetch the TDEE for the user name in the session
            sql = "SELECT tdee FROM user_metrics_history WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()

        if result:
            tdee = result['tdee']
            return jsonify({"status": "success", "tdee": round(tdee, 2)})
        else:
            return jsonify({"status": "error", "message": "User not found"}), 404

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return jsonify({"status": "error", "message": "Failed to get TDEE"}), 500
    
    
@app.route('/api/profile', methods=['POST'])
def save_profile():
    try:
        data = request.json

        #data from the form 
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        gender = data.get('gender')
        age = int(data.get('age'))
        height = float(data.get('height'))
        weight = float(data.get('weight'))
        goals = data.get('goals')
        difficulty = data.get('difficulty')
        activity = data.get('activity')

        #activity
        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'active': 1.725,
            'very-active': 1.9
        }

        # Here is the formula
        if gender == 'male':
            bmr = (4.536 * weight) + (15.88 * height) - (5 * age) + 5
        else:
            bmr = (4.536 * weight) + (15.88 * height) - (5 * age) - 161

        if difficulty == 'beginner':
            calo = 200
        elif difficulty == 'intermediate':
            calo = 350
        elif difficulty == 'advanced':
            calo = 500

        # Calculate the TDEE (Total Daily Energy Expenditure)
        if goals == 'weight-loss':
            tdee = bmr * activity_multipliers[activity] - calo  # Create a calorie deficit
        elif goals == 'muscle-gain':
            tdee = bmr * activity_multipliers[activity] + calo  # Create a calorie surplus
        else:
            tdee = bmr * activity_multipliers[activity]  # Maintenance

        # max macros 
        if goals == 'weight-loss':
            max_proteins = 0.3 * tdee / 4
            max_carbs = 0.4 * tdee / 4
            max_fats = 0.3 * tdee / 9
            
        elif goals == 'muscle-gain':
            max_proteins = 0.4 * tdee / 4
            max_carbs = 0.3 * tdee / 4
            max_fats = 0.3 * tdee / 9
            
        else:
            max_proteins = 0.3 * tdee / 4
            max_carbs = 0.4 * tdee / 4
            max_fats = 0.3 * tdee / 9

        db = g.db
        with db.cursor() as cursor:
            if 'user_id' in session:
                # UPDATE MODE
                user_id = session['user_id']
                sql_update_user = """UPDATE users SET name=%s, age=%s, weight=%s, height=%s WHERE id=%s"""
                cursor.execute(sql_update_user, (name, age, weight, height, user_id))
                
                # Insert new metrics entry (History)
                sql_user_metrics_history = """INSERT INTO user_metrics_history 
                (user_id, tdee, max_proteins, max_carbs, max_fats, activity, goals, difficulty)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                values_user_metrics_history = (user_id, tdee, max_proteins, max_carbs, max_fats, activity, goals, difficulty)
                cursor.execute(sql_user_metrics_history, values_user_metrics_history)
            else:
                # SIGNUP MODE
                # Check if email already exists
                sql_check_email = "SELECT user_id FROM login WHERE email = %s"
                cursor.execute(sql_check_email, (email,))
                if cursor.fetchone():
                    return jsonify({"status": "error", "message": "Email already registered"}), 409

                # Hash the password
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                # users table
                sql_users = """INSERT INTO users (name, age, gender, weight, height)
                VALUES (%s, %s, %s, %s, %s)"""
                values_users = (name, age, gender, weight, height)
                cursor.execute(sql_users, values_users)

                # Retrieve the id of the newly created user
                user_id = cursor.lastrowid 

                # login table
                sql_login = """INSERT INTO login (user_id, email, password_hash)
                VALUES (%s, %s, %s)"""
                values_login = (user_id, email, hashed_password)
                cursor.execute(sql_login, values_login)

                # Insert into user_metrics_history table
                sql_user_metrics_history = """INSERT INTO user_metrics_history (user_id, tdee, max_proteins, max_carbs, max_fats, activity, goals, difficulty)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                values_user_metrics_history = (user_id, tdee, max_proteins, max_carbs, max_fats, activity, goals, difficulty)
                cursor.execute(sql_user_metrics_history, values_user_metrics_history)

            db.commit()
            return jsonify({"status": "success", "message": "Profile saved successfully!", "tdee": round(tdee, 2)})
    
    except Exception as e:
        if 'db' in g and g.db.is_connected():
            g.db.rollback()
        print(f"Error in save_profile: {e}")
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500
   
@app.route('/api/add_food', methods=['POST'])
def add_food_entry():
    # Ensure the user is logged in
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401
    
    data = request.get_json()
    user_id = session['user_id']
    product_name = data.get('product_name')
    serving_size_grams = data.get('serving_size')

    # Nutritional info per 100g from the API, passed from the client
    calories_per_100g = data.get('calories')
    proteins_per_100g = data.get('proteins')
    carbs_per_100g = data.get('carbohydrates')
    fats_per_100g = data.get('fat')

    # Validate required fields: Use explicit None checks to allow 0 values
    required_vals = [product_name, serving_size_grams, calories_per_100g, proteins_per_100g, carbs_per_100g, fats_per_100g]
    if any(v is None for v in required_vals):
        return jsonify({'status': 'error', 'message': 'Missing product name or serving size'}), 400

    try:
        serving_size = float(serving_size_grams)
        calories_per_100g = float(calories_per_100g)
        proteins_per_100g = float(proteins_per_100g)
        carbs_per_100g = float(carbs_per_100g)
        fats_per_100g = float(fats_per_100g)
    except (ValueError, TypeError):
        return jsonify({'status': 'error', 'message': 'Invalid data type for nutritional values or serving size'}), 400

    today_date = date.today()

    try:
        db = g.db
        with db.cursor(dictionary=True) as cursor:
            # Check if the product already exists in nutrition_data
            sql_find_product = "SELECT product_id FROM nutrition_data WHERE product_name = %s"
            cursor.execute(sql_find_product, (product_name,))
            product = cursor.fetchone()

            if product:
                product_id = product['product_id']
            else:
                # Insert new product into nutrition_data if it doesn't exist
                sql_insert_product = """INSERT INTO nutrition_data (product_name, calories_per_100g, proteins_per_100g, carbs_per_100g, fats_per_100g)
                                      VALUES (%s, %s, %s, %s, %s)"""
                product_values = (product_name, calories_per_100g, proteins_per_100g, carbs_per_100g, fats_per_100g)
                cursor.execute(sql_insert_product, product_values)
                product_id = cursor.lastrowid

            # Insert the food entry with calculated nutritional values for the serving size
            sql_food_entries = """INSERT INTO food_entries (user_id, nutrition_id, serving_size, entry_date)
                                  VALUES (%s, %s, %s, %s)"""
            values_food_entries = (user_id, product_id, serving_size, today_date)
            cursor.execute(sql_food_entries, values_food_entries)
            
            db.commit()
            return jsonify({'status': 'success', 'message': 'Food entry added successfully!'}), 201

    except mysql.connector.Error as err:
        app.logger.error(f"database error adding food entry: {err}")
        return jsonify({'status': 'error', 'message': 'Failed to add food entry'}), 500

@app.route('/api/get_daily_totals', methods=['GET'])
def get_daily_totals():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401
    
    user_id = session['user_id']
    today = date.today()

    try: 
        db = g.db
        with db.cursor(dictionary=True) as cursor:
            sql_goals = '''SELECT tdee, max_proteins, max_carbs, max_fats
            FROM user_metrics_history
            WHERE user_id = %s
            ORDER BY updated_at DESC LIMIT 1'''
            cursor.execute(sql_goals, (user_id,))
            goals = cursor.fetchone()

            if not goals:
                return jsonify({
                    'status': 'error',
                    'message': 'User goals not found'
                }), 404

            # Calculate daily totals for today
            sql_totals = '''SELECT SUM(nd.calories_per_100g / 100 * fe.serving_size) AS total_calories,
            SUM(nd.proteins_per_100g / 100 * fe.serving_size) AS total_proteins,
            SUM(nd.carbs_per_100g / 100 * fe.serving_size) AS total_carbs,
            SUM(nd.fats_per_100g / 100 * fe.serving_size) AS total_fats
            FROM food_entries fe
            JOIN nutrition_data nd ON fe.nutrition_id = nd.product_id
            WHERE fe.user_id = %s AND fe.entry_date = %s'''
            cursor.execute(sql_totals, (user_id, today))
            totals = cursor.fetchone()

            response_data = calculate_nutritional_data(goals, totals)
            return jsonify({'status': 'success', 'data':response_data}), 200
            
    except mysql.connector.Error as err:
        app.logger.error(f"Database error: {err}")
        return jsonify({'status': 'error', 'message': 'Database error'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error'})

if __name__ == "__main__":
        # Local Dev
        print("\n --- Dev MODE on: https://localhost:5000 --- \n")
        app.run(host='0.0.0.0', port=5000, debug=True, ssl_context='adhoc')
