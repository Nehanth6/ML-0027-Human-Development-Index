# importing the necessary dependencies
import os
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, session, redirect, url_for, flash
import pickle
import joblib
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client

app = Flask(__name__) # initializing a flask app
app.secret_key = 'your_super_secret_key_here' # For Flask sessions and flash messages

# Initialize Supabase Client
SUPABASE_URL = "https://ssbdgjfewwoddouyiusa.supabase.co"
SUPABASE_KEY = "sb_publishable_QNiOeW59hvRYXWQe7s7VxQ_QZM8z-BB"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Load the model
try:
    model = pickle.load(open('HDI.pkl', 'rb'))
except:
    model = joblib.load('hdi_model.pkl')

# --- AUTHENTICATION DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/Home', methods=['POST', 'GET'])
def my_home():
    return render_template('home.html')

@app.route('/Prediction', methods=['POST', 'GET'])
@login_required
def prediction():
    return render_template('indexnew.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user already exists
        response = supabase.table('users').select('*').eq('email', email).execute()
        if len(response.data) > 0:
            flash("An account with that email already exists.", "error")
            return redirect(url_for('register'))

        # Hash password and save to Supabase
        hashed_password = generate_password_hash(password)
        try:
            supabase.table('users').insert({
                "name": name,
                "email": email,
                "password_hash": hashed_password,
                "role": "user"
            }).execute()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Find user
        response = supabase.table('users').select('*').eq('email', email).execute()
        if len(response.data) == 0:
            flash("Invalid email or password.", "error")
            return redirect(url_for('login'))

        user = response.data[0]
        
        # Verify password
        if check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            
            # Record login in SESSION table
            try:
                session_res = supabase.table('session').insert({
                    "user_id": user['user_id'],
                    "login_time": "now()",
                    "status": "active"
                }).execute()
                session['session_id'] = session_res.data[0]['session_id']
            except:
                pass # If session tracking fails, still allow login
                
            return redirect(url_for('prediction'))
        else:
            flash("Invalid email or password.", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    # Update logout time if we have a session_id
    if 'session_id' in session:
        try:
            supabase.table('session').update({
                "logout_time": "now()",
                "status": "completed"
            }).eq('session_id', session['session_id']).execute()
        except:
            pass
            
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    # Read inputs
    region_id = int(request.form.get('Region'))
    life_expectancy = float(request.form.get('Life_expectancy'))
    mean_schooling = float(request.form.get('Mean_schooling'))
    gni = float(request.form.get('GNI'))
    
    input_features = [region_id, life_expectancy, mean_schooling, gni]
    features_value = [np.array(input_features)]
    
    features_name = ['Region', 'Life expectancy', 'Mean years of schooling', 'Gross national income (GNI) per capita']
    df = pd.DataFrame(features_value, columns=features_name)
    
    # Generate prediction
    output = model.predict(df)
    
    if isinstance(output, np.ndarray) and len(output.shape) > 0:
        y_pred = round(output[0], 2)
    else:
        y_pred = round(output, 2)
        
    # Determine category
    if 0.3 <= y_pred <= 0.4:
        category = "Low HDI"
    elif 0.4 < y_pred <= 0.7:
        category = "Medium HDI"
    elif 0.7 < y_pred <= 0.8:
        category = "High HDI"
    elif 0.8 < y_pred <= 0.94:
        category = "Very High HDI"
    else:
        category = "Unknown"

    prediction_text = f"{category} {y_pred}"

    # --- SAVE TO SUPABASE ---
    try:
        # 1. Insert Input Data (Mock country_id for now as 1, or use Region as country_id)
        # Note: You'll want to map Region to a real country_id later, but we use region_id for now.
        input_data = {
            "user_id": session['user_id'],
            "country_id": 1, # Default placeholder until country selection is added
            "life_expectancy": life_expectancy,
            "mean_years_schooling": mean_schooling,
            "expected_years_schooling": 0.0, # Not collected in form
            "gni_per_capita": gni
        }
        input_res = supabase.table('hdi_input_data').insert(input_data).execute()
        inserted_input_id = input_res.data[0]['input_id']

        # 2. Insert Prediction
        prediction_data = {
            "input_id": inserted_input_id,
            "model_id": 1, # Default model ID
            "predicted_hdi_score": y_pred,
            "hdi_category": category
        }
        supabase.table('hdi_prediction').insert(prediction_data).execute()
    except Exception as e:
        print("Database Error:", e) # Log error but don't crash user experience

    return render_template("resultnew.html", prediction_text=prediction_text)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
