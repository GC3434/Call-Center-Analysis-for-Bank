from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
import sqlite3
import pandas as pd
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
import speech_recognition as sr
from collections import defaultdict
import os
import joblib
import datetime

app = Flask(__name__)
app.secret_key = '5766ghghgg7654dfd7h9hsfsfh'



@app.route('/')
def home():
    return render_template('signup.html')

##################################################################################################################################

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        
        name = request.form['name']
        designation = request.form['designation']
        email = request.form['email']
        contact = request.form['contact']
        employee_id = request.form['employee_id']
        password = request.form['password']
        re_password = request.form['re_password']
        
        # Check if email already exists in the database
        conn = sqlite3.connect('D:\\call_center_bank\\call_center_bank\\flask\\database\\user.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_details WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user is not None:
            # If the user already exists, add a flash message and redirect back to the signup page
            session['message'] = 'email already exist. Please go to login page.'
            
            return redirect(url_for('signup', error='email already exist.'))
        
        
        elif  password != re_password:
            
            session['message'] = 'Both password are different.'
            
            return redirect(url_for('signup', error='password do not match.'))
                
        
        else:
            # If the user does not exist, insert the new user into the database and redirect to the login page
            conn = sqlite3.connect('D:\\call_center_bank\\call_center_bank\\flask\\database\\user.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO user_details (name, designation, email, contact, employee_id, password, re_password) VALUES (?, ?, ?, ?, ?, ?, ?)", (name, designation, email, contact, employee_id, password, re_password))
            conn.commit()
            conn.close()
            
            return redirect(url_for('login'))
        
    elif request.args.get('error') is None:    
        return render_template('signup.html')
        
    else:   
        error = request.args.get('error')
        return render_template('signup.html', error=error)



@app.route('/login', methods=['GET', 'POST'])
def login():
   if request.method == 'POST':
       
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('D:\\call_center_bank\\call_center_bank\\flask\\database\\user.db')
        c = conn.cursor()
        
        c.execute("SELECT * FROM user_details WHERE email = ? AND password = ?", (email, password))
        user = c.fetchone()
        conn.close()
        
        if user is not None:
            session['email'] = user[2]
            return redirect(url_for('homepage'))
        else:
            return render_template('login.html', error='Invalid email or password')
   else:
        return render_template('login.html')


@app.route('/index')
def index():
    if 'email' in session:
        return render_template('homepage.html', current_user=session['email'])
    return redirect(url_for('login'))   


##########################################################################################################################################

# Load the dataset from CSV file
df = pd.read_csv('customer_complaints.csv')

# Create feature vectors
vectorizer = CountVectorizer()
vectorizer.fit_transform(df['complain'])

model = joblib.load('model_rf.pkl')

@app.route("/homepage", methods=["GET", "POST"])
def homepage():
    return render_template('homepage.html')


@app.route('/dashboard')
def dashboard():
    # Connect to SQLite database
    conn = sqlite3.connect('D:\\call_center_bank\\call_center_bank\\flask\\database\\user.db')
    cursor = conn.cursor()

    # Retrieve the day-wise complaint counts from the database
    cursor.execute("SELECT strftime('%w', day), COUNT(*) FROM domain GROUP BY strftime('%w', day)")
    day_counts = cursor.fetchall()

    # Initialize a dictionary to store the day-wise counts
    counts_by_day = defaultdict(int)

    # Process the fetched data and populate the dictionary
    for row in day_counts:
        day = row[0]
        count = row[1]
        counts_by_day[day] = count

    # Create a list of days of the week in the correct order
    days_of_week = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    # Prepare the data for the bar chart
    daywise_counts = [counts_by_day[str(day)] for day in range(7)]
    
    
    cursor.execute("SELECT domain, COUNT(*) FROM domain GROUP BY domain")
    domain_counts = cursor.fetchall()

    # Close the database connection
    conn.close()

    # Prepare the data for the pie chart
    domains = [row[0] for row in domain_counts]
    counts = [row[1] for row in domain_counts]

    # Render the dashboard template with the day-wise complaint counts
    return render_template('dashboard.html', days=days_of_week, daywise_counts=daywise_counts, domains=domains, counts=counts)




@app.route("/upload", methods=["GET", "POST"])
def upload():
    complaint = None
    prediction = None
    
    if request.method == "POST":
        # Save the uploaded image to a file
        audio = request.files['audio']
        audio_path = 'static/audio/' + audio.filename
        audio.save(audio_path)

        # Initialize the speech recognition recognizer
        recognizer = sr.Recognizer()

        # Load the audio file
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)

        # Convert speech to text

        complaint = recognizer.recognize_google(audio)
        
        # Convert complaint to feature vector
        complaint_vector = vectorizer.transform([complaint])

        # Make the domain prediction
        prediction = model.predict(complaint_vector)
        prediction = prediction[0]
        
         # Connect to SQLite database
        conn = sqlite3.connect('D:\\call_center_bank\\call_center_bank\\flask\\database\\user.db')
        cursor = conn.cursor()
        
        # Get the current day
        current_day = datetime.date.today().strftime("%Y-%m-%d")

        # Insert the complaint, prediction, and day into the database
        cursor.execute("INSERT INTO domain (complaint, domain, day) VALUES (?, ?, ?)", (complaint, prediction, current_day))
        conn.commit()

        # Close the database connection
        conn.close()

        # Clean up the temporary WAV file
        os.remove(audio_path)
    
    return render_template('upload.html', cp=complaint, src=prediction)

if __name__ == "__main__":
    app.run(debug=True)
