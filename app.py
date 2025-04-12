# app.py
from flask import Flask, render_template, redirect, request, url_for, session, flash
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from config import MONGO_URI, SECRET_KEY
from bson.objectid import ObjectId
app = Flask(__name__)

app.secret_key = SECRET_KEY
app.config["MONGO_URI"] = MONGO_URI


mongo = PyMongo(app)
bcrypt = Bcrypt(app)

@app.route('/')
def home():
    return redirect(url_for('login'))

# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'username': request.form['username']})
        
        if existing_user:
            flash('Username already exists!')
            return redirect(url_for('register'))

        hashpass = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        users.insert_one({'username': request.form['username'], 'password': hashpass})
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = mongo.db.users
        user = users.find_one({'username': request.form['username']})

        if user and bcrypt.check_password_hash(user['password'], request.form['password']):
            session['username'] = request.form['username']
            flash('Login successful!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.')
            return redirect(url_for('login'))

    return render_template('login.html')

# LOGOUT
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.')
    return redirect(url_for('login'))

# ADD STUDENT
@app.route('/add', methods=['GET', 'POST'])
def add_student():
    if 'username' not in session:
        flash("Please login first.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        students = mongo.db.students
        students.insert_one({
            'name': request.form['name'],
            'roll': request.form['roll'],
            'course': request.form['course'],
            'created_by': session['username']  # 👈 Save who created this student
        })
        flash("Student added successfully.")
        return redirect(url_for('dashboard'))

    return render_template('add_student.html')


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash("Please login first.", 'error')
        return redirect(url_for('login'))

    search_query = request.args.get('search', '').strip()
    students_collection = mongo.db.students

    if search_query:
        students = students_collection.find({
            'name': {'$regex': search_query, '$options': 'i'},
            'created_by': session['username']
        })
    else:
        students = students_collection.find({'created_by': session['username']})

    return render_template('dashboard.html', students=list(students), search_query=search_query)


# EDIT STUDENT
@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit_student(id):
    if 'username' not in session:
        flash("Please login first.")
        return redirect(url_for('login'))

    students = mongo.db.students
    student = students.find_one({'_id': ObjectId(id)})

    if request.method == 'POST':
        students.update_one(
            {'_id': ObjectId(id)},
            {"$set": {
                'name': request.form['name'],
                'roll': request.form['roll'],
                'course': request.form['course']
            }}
        )
        flash("Student updated successfully.")
        return redirect(url_for('dashboard'))

    return render_template('edit_student.html', student=student)


# DELETE STUDENT
@app.route('/delete/<id>')
def delete_student(id):
    if 'username' not in session:
        flash("Please login first.")
        return redirect(url_for('login'))

    mongo.db.students.delete_one({'_id': ObjectId(id)})
    flash("Student deleted successfully.")
    return redirect(url_for('dashboard'))

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        users = mongo.db.users
        username = request.form['username']
        new_password = request.form['new_password']

        user = users.find_one({'username': username})
        if not user:
            flash("Username not found!", 'error')
            return redirect(url_for('reset_password'))

        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        users.update_one({'username': username}, {'$set': {'password': hashed_password}})
        flash("Password updated successfully! Please login.", 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

from datetime import datetime

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}


if __name__ == '__main__':
    # print("Available routes:")
    # for rule in app.url_map.iter_rules():
    #     print(rule)
    app.run(debug=True)