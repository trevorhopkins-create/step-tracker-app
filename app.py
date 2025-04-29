from flask import Flask, render_template, request, redirect, url_for, session
from flask import flash, get_flashed_messages
import json
import os
from datetime import datetime

import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

MONTHLY_GOAL = 100000  # <-- Set your goal here (you can change later)

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Used to manage sessions (users staying logged in)

# Files
USERS_FILE = 'users.json'
STEPS_FILE = 'steps.json'

# Load or create users/steps
def load_data():
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            users = json.load(f)
    else:
        users = {}

    if os.path.exists('steps.json'):
        with open('steps.json', 'r') as f:
            steps = json.load(f)
    else:
        steps = {}

    # 🛠 Upgrade simple users to full object with password + goal
    for username, data in list(users.items()):
        if isinstance(data, str):
            users[username] = {
                "password": data,
                "goal": 100000  # Default goal
            }

    return users, steps


def save_data(users, steps):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)
    with open(STEPS_FILE, 'w') as f:
        json.dump(steps, f)

@app.route('/', methods=['GET', 'POST'])
def login():
    users, steps = load_data()
    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            session['username'] = username
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password.", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')


   
@app.route('/register', methods=['GET', 'POST'])
def register():
    users, steps = load_data()
    if request.method == 'POST':
        username = request.form['username'].lower()
        password = request.form['password']
        if username in users:
            return "Username already exists."
        users[username] = password
        save_data(users, steps)
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))
        
    return render_template('register.html')


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    users, steps = load_data()
    if request.method == 'POST':
        username = request.form['username'].lower()
        new_password = request.form['new_password']

        if username in users:
            users[username]['password'] = new_password
            save_data(users, steps)
            flash("Password reset successfully! Please log in.", "success")
            return redirect(url_for('login'))
        else:
            flash("Username not found.", "danger")
            return redirect(url_for('reset_password'))

    return render_template('reset_password.html')



@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']

    users, steps_data = load_data()

    if request.method == 'POST':
        today = datetime.now().strftime("%Y-%m-%d")
        date = request.form.get('date', today)
        steps_taken = int(request.form['steps'])

        if username not in steps_data:
            steps_data[username] = []
        steps_data[username].append({'date': date, 'steps': steps_taken})
        save_data(users, steps_data)

        flash("Steps added successfully!", "success")
        return redirect(url_for('dashboard'))


    user_steps = steps_data.get(username, [])
    current_month = datetime.now().strftime("%Y-%m")
    monthly_steps = sum(entry['steps'] for entry in user_steps if entry['date'].startswith(current_month))

    user_goal = users[username].get('goal', 100000)

    progress_percent = int((monthly_steps / user_goal) * 100) if user_goal else 0
    if progress_percent > 100:
        progress_percent = 100

    # Milestones
    unlocked_badges = []
    if progress_percent >= 25:
        unlocked_badges.append("25% Milestone 🥉 Bronze Badge")
    if progress_percent >= 50:
        unlocked_badges.append("50% Milestone 🥈 Silver Badge")
    if progress_percent >= 75:
        unlocked_badges.append("75% Milestone 🥇 Gold Badge")
    if progress_percent >= 100:
        unlocked_badges.append("100% Milestone 🏆 Champion Badge")

    # Progress Bar Color
    if progress_percent < 25:
        progress_color = "danger"
    elif progress_percent < 75:
        progress_color = "warning"
    else:
        progress_color = "success"

    # ✅ THIS IS STILL INSIDE the function
    return render_template(
        'dashboard.html',
        monthly_steps=monthly_steps,
        progress_percent=progress_percent,
        user_goal=user_goal,
        progress_color=progress_color,
        username=username,
        unlocked_badges=unlocked_badges
    )


@app.route('/update_goal', methods=['POST'])
def update_goal():
    if 'username' not in session:
        return redirect(url_for('login'))

    users, steps = load_data()
    username = session['username']

    new_goal = int(request.form['goal'])

    if username in users:
        users[username]['goal'] = new_goal
        save_data(users, steps)
        flash("Monthly goal updated successfully!", "success")

    return redirect(url_for('dashboard'))


@app.route('/history')
def history():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    steps_data = load_steps()
    user_steps = steps_data.get(session['username'], [])
    user_steps.sort(key=lambda x: x['date'])
    return render_template('history.html', steps=user_steps)


@app.route('/edit_step/<date>', methods=['GET', 'POST'])
def edit_step(date):
    if 'username' not in session:
        return redirect(url_for('login'))

    steps_data = load_steps()
    user_steps = steps_data.get(session['username'], [])

    if request.method == 'POST':
        new_steps = int(request.form['steps'])
        for entry in user_steps:
            if entry['date'] == date:
                entry['steps'] = new_steps
                break
        save_data(load_users(), steps_data)
        flash(f"Steps for {date} updated successfully!", "success")
        return redirect(url_for('history'))

    current_steps = None
    for entry in user_steps:
        if entry['date'] == date:
            current_steps = entry['steps']
            break

    if current_steps is None:
        flash("Step entry not found.", "danger")
        return redirect(url_for('history'))

    return render_template('edit_step.html', date=date, steps=current_steps)


@app.route('/delete_step/<date>')
def delete_step(date):
    if 'username' not in session:
        return redirect(url_for('login'))

    steps_data = load_steps()
    user_steps = steps_data.get(session['username'], [])

    steps_data[session['username']] = [entry for entry in user_steps if entry['date'] != date]

    save_data(load_users(), steps_data)
    flash(f"Steps for {date} deleted successfully!", "success")
    return redirect(url_for('history'))


@app.route('/totals')
def totals():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    steps_data = load_steps()
    user_steps = steps_data.get(session['username'], [])
    total_steps = sum(entry['steps'] for entry in user_steps)
    return render_template('totals.html', total=total_steps)

@app.route('/leaderboard')
def leaderboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    steps_data = load_steps()
    leaderboard_data = []
    for user, entries in steps_data.items():
        total = sum(entry['steps'] for entry in entries)
        leaderboard_data.append((user, total))
    leaderboard_data.sort(key=lambda x: x[1], reverse=True)

    return render_template('leaderboard.html', leaderboard=leaderboard_data)

@app.route('/graph')
def graph():
    if 'username' not in session:
        return redirect(url_for('login'))

    steps_data = load_steps()
    user_steps = steps_data.get(session['username'], [])

    if not user_steps:
        return "No steps data to plot."

    user_steps.sort(key=lambda x: x['date'])
    dates = [entry['date'] for entry in user_steps]
    steps = [entry['steps'] for entry in user_steps]

    plt.figure(figsize=(10, 6))
    plt.plot(dates, steps, marker='o')
    plt.title(f"{session['username'].capitalize()}'s Steps Over Time")
    plt.xlabel("Date")
    plt.ylabel("Steps")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    graph_path = os.path.join('static', f"{session['username']}_graph.png")
    plt.savefig(graph_path)
    plt.close()

    return render_template('graph.html', graph_file=f"{session['username']}_graph.png")

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Helper functions
def load_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def load_steps():
    with open(STEPS_FILE, 'r') as f:
        return json.load(f)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)