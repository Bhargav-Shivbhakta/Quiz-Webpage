from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
import os

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB Atlas connection
client = MongoClient("mongodb+srv://aarya:aarya123@cluster0.n4p9pyd.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['mindmaze_db']

# Collections
users_col = db['users']
quizzes_col = db['quizzes']
results_col = db['results']

# Routes
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        existing_user = users_col.find_one({'username': username})
        if existing_user:
            flash('Username already exists.')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        users_col.insert_one({'username': username, 'password': hashed_password, 'role': role})
        flash('Signup successful! Please login.')
        return redirect(url_for('home'))

    return render_template('signup.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    user = users_col.find_one({'username': username})

    if user and check_password_hash(user['password'], password):
        session['username'] = username
        session['role'] = user['role']

        if user['role'] == 'conductor':
            return redirect(url_for('conductor_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    else:
        flash('Invalid credentials!')
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/conductor/dashboard')
def conductor_dashboard():
    if 'username' not in session or session['role'] != 'conductor':
        return redirect(url_for('home'))
    return render_template('conductor_dashboard.html')

@app.route('/conductor/create_quiz', methods=['GET', 'POST'])
def create_quiz():
    if 'username' not in session or session['role'] != 'conductor':
        return redirect(url_for('home'))

    if request.method == 'POST':
        quiz_name = request.form['quiz_name']
        questions = []

        total_questions = int(request.form['total_questions'])
        for i in range(1, total_questions + 1):
            question = request.form[f'question_{i}']
            options = [
                request.form[f'option1_{i}'],
                request.form[f'option2_{i}'],
                request.form[f'option3_{i}'],
                request.form[f'option4_{i}']
            ]
            correct_option = int(request.form[f'correct_option_{i}'])
            questions.append({'question': question, 'options': options, 'correct_option': correct_option})

        quizzes_col.insert_one({'conductor': session['username'], 'quiz_name': quiz_name, 'questions': questions})
        flash('Quiz created successfully!')
        return redirect(url_for('conductor_dashboard'))

    return render_template('create_quiz.html')

@app.route('/student/dashboard')
def student_dashboard():
    if 'username' not in session or session['role'] != 'student':
        return redirect(url_for('home'))

    quizzes = list(quizzes_col.find())
    return render_template('student_dashboard.html', quizzes=quizzes)

@app.route('/quiz/<quiz_id>', methods=['GET', 'POST'])
def attempt_quiz(quiz_id):
    if 'username' not in session or session['role'] != 'student':
        return redirect(url_for('home'))

    quiz = quizzes_col.find_one({'_id': ObjectId(quiz_id)})
    if request.method == 'POST':
        answers = []
        correct_count = 0

        for idx, q in enumerate(quiz['questions']):
            selected = int(request.form.get(f'question_{idx}', -1))
            answers.append(selected)
            if selected == q['correct_option']:
                correct_count += 1

        results_col.insert_one({
            'student': session['username'],
            'quiz_id': quiz_id,
            'score': correct_count,
            'total': len(quiz['questions']),
            'answers': answers
        })

        return redirect(url_for('view_result', quiz_id=quiz_id))

    return render_template('attempt_quiz.html', quiz=quiz)

@app.route('/result/<quiz_id>')
def view_result(quiz_id):
    if 'username' not in session or session['role'] != 'student':
        return redirect(url_for('home'))

    result = results_col.find_one({'student': session['username'], 'quiz_id': quiz_id})
    return render_template('result.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)
