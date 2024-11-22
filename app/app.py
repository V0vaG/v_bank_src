from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import socket
from functools import wraps
from funcs import *
from datetime import datetime


# Configuration
app = Flask(__name__)
app.secret_key = 'supersecretkey'
version = os.getenv('B_NUM', '0.0.0')
host = socket.gethostname()

# Set up paths
alias = "v_bank"
HOME_DIR = os.path.expanduser("~")
FILES_PATH = os.path.join(HOME_DIR, "script_files", alias)
DATA_DIR = os.path.join(FILES_PATH, "data")
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
ADMINS_FILE = os.path.join(DATA_DIR, 'admins.json')

# Ensure the directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Ensure both files exist
for file in [USERS_FILE, ADMINS_FILE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump([], f)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Determine if the new account is a user or an admin
        role = request.form.get('role', 'user')
        users_file = USERS_FILE if role == 'user' else ADMINS_FILE



        # Load the appropriate file
        with open(users_file, 'r') as f:
            users = json.load(f)

        # Extract form data
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if username already exists
        if any(user['username'] == username for user in users):
            flash(f"Username '{username}' already exists.", "danger")
            return redirect(url_for('register'))

        # Hash the password before saving it
        hashed_password = generate_password_hash(password)

        # Create a new user object
        new_user = {'username': username, 'password': hashed_password, 'kind': role}

        # Additional fields for users
        if role == 'user':
            name = request.form.get('name')
            birthday = request.form.get('birthday')
            balance = request.form.get('balance', 0)
            sellery = request.form.get('sellery', 0)
            interest = request.form.get('interest', 0)
            overdraft = request.form.get('overdraft', 0)
            new_user.update({
                'name': name,
                'birthday': birthday,
                'balance': int(balance),
                'sellery': int(sellery),
                'interest': int(interest),
                'overdraft': int(overdraft)
            })

        print(f"Saving to file: {users_file}")
        print(f"New user data: {new_user}")

        # Append the new user or admin to the list
        users.append(new_user)

        # Save the updated list to the file
        with open(users_file, 'w') as f:
            json.dump(users, f, indent=4)

        flash(f"User created successfully as {role}!", "success")
        return redirect(url_for('show_login'))

    # If GET, show the registration form
    show_role_selection = 'admin_area' in request.args
    back_url = url_for('admin_area') if 'admin_area' in request.args else url_for('show_login')
    return render_template('register.html', show_role_selection=show_role_selection, back_url=back_url)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    def find_user(file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                users = json.load(f)
            return next((u for u in users if u['username'] == username), None)
        return None

    # Search for the user in both files
    user = find_user(USERS_FILE) or find_user(ADMINS_FILE)

    # Validate user and password
    if user and check_password_hash(user['password'], password):
        session['active_user'] = username
        session['active_role'] = user['kind']  # Store the role (admin or user)
        flash("Login successful!", "success")
        return redirect(url_for('home'))

    flash("Invalid username or password.", "danger")
    return redirect(url_for('show_login'))


@app.route('/')
def show_login():
    # Load users from the JSON file
    users_file = os.path.join(DATA_DIR, 'users.json')
    if os.path.exists(users_file):
        with open(users_file, 'r') as f:
            users = json.load(f)
    else:
        users = []

    # Check if there are no users
    no_users_exist = len(users) == 0

    # Load the external registration setting
    config_file = os.path.join(DATA_DIR, 'config.json')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        config = {"allow_registration": False}

    allow_registration = config.get('allow_registration', False)

    return render_template('login.html', no_users_exist=no_users_exist, allow_registration=allow_registration)

@app.route('/logout')
def logout():
    session.pop('active_user', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('show_login'))

# Move this decorator definition to a standalone section of the code
def login_required(f):
    @wraps(f)  # This preserves the original function name and prevents overwriting issues
    def wrap(*args, **kwargs):
        if 'active_user' not in session:
            flash("You need to login first.", "danger")
            return redirect(url_for('show_login'))
        return f(*args, **kwargs)
    return wrap

@app.route('/index', methods=['GET', 'POST'])
@login_required
def home():
    username = session.get('active_user')
    role = session.get('active_role')  # Get the user's role (admin or user)

    # Load the appropriate file based on the role
    file_path = ADMINS_FILE if role == 'admin' else USERS_FILE
    with open(file_path, 'r') as f:
        users = json.load(f)

    # Find the logged-in user's data
    user = next((u for u in users if u['username'] == username), None)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('show_login'))

    # Render admin or user-specific page
    if role == 'admin':
        return redirect(url_for('admin_area'))  # Redirect admins to the admin area
    else:
        # Handle regular user page logic
        return render_template(
            'index.html',
            version=version,
            host=host,
            user=user,
            role=role,
            current_year=datetime.now().year
        )

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_area():
    username = session.get('active_user')
    role = session.get('active_role')

    # Ensure the logged-in user is an admin
    if role != 'admin':
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('home'))

    # Load all admins
    with open(ADMINS_FILE, 'r') as f:
        admins = json.load(f)

    # Load all users
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    # Render the admin page
    return render_template(
        'admin.html',
        admin_data=admins,
        users=users,
        version=version,
        host=host
    )

@app.route('/edit_user/<username>', methods=['GET', 'POST'])
@login_required
def edit_user(username):
    # Ensure the logged-in user is an admin
    active_username = session.get('active_user')
    role = session.get('active_role')

    if role != 'admin':
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('home'))

    # Load all users
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    # Find the user to edit
    user = next((u for u in users if u['username'] == username), None)
    if not user:
        flash(f"User '{username}' not found.", "danger")
        return redirect(url_for('admin_area'))

    if request.method == 'POST':
        # Update user details
        user['name'] = request.form.get('name')
        user['birthday'] = request.form.get('birthday')
        user['balance'] = int(request.form.get('balance', 0))
        user['sellery'] = int(request.form.get('sellery', 0))
        user['interest'] = int(request.form.get('interest', 0))
        user['overdraft'] = int(request.form.get('overdraft', 0))
        user['kind'] = request.form.get('role')

        # Handle password change
        new_password = request.form.get('password')
        if new_password:
            user['password'] = generate_password_hash(new_password)

        # Save updated users list
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=4)

        flash(f"User '{username}' updated successfully.", "success")
        return redirect(url_for('admin_area'))

    return render_template('edit_user.html', user=user)


@app.route('/delete_user/<username>', methods=['POST'])
@login_required
def delete_user(username):
    # Ensure the logged-in user is an admin
    active_username = session.get('active_user')
    role = session.get('active_role')

    if role != 'admin':
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('home'))

    # Determine which file to search (admins or users)
    target_file = ADMINS_FILE if any(
        admin.get('username') == username for admin in json.load(open(ADMINS_FILE))
    ) else USERS_FILE

    # Load the target file data
    with open(target_file, 'r') as f:
        users = json.load(f)

    # Ensure the user isn't trying to delete themselves if they're an admin
    if target_file == ADMINS_FILE and active_username == username:
        flash("You cannot delete yourself as an admin.", "danger")
        return redirect(url_for('admin_area'))

    # Filter out the user to be deleted
    updated_users = [user for user in users if user['username'] != username]

    # Save the updated user list
    with open(target_file, 'w') as f:
        json.dump(updated_users, f, indent=4)

    flash(f"User '{username}' has been deleted.", "success")
    return redirect(url_for('admin_area'))


@app.route('/adjust_balance/<username>', methods=['POST'])
@login_required
def adjust_balance(username):
    # Ensure the logged-in user is an admin
    active_username = session.get('active_user')
    role = session.get('active_role')

    if role != 'admin':
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('home'))

    # Load the users from USERS_FILE
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    # Find the user whose balance is to be adjusted
    user = next((u for u in users if u['username'] == username), None)
    if not user:
        flash(f"User '{username}' not found.", "danger")
        return redirect(url_for('admin_area'))

    # Adjust the user's balance
    try:
        amount = int(request.form.get('amount'))
        user['balance'] += amount

        # Save the updated users data
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=4)

        flash(f"User '{username}' balance updated by {amount}. New balance: {user['balance']}.", "success")
    except ValueError:
        flash("Invalid amount entered. Please enter a valid number.", "danger")

    return redirect(url_for('admin_area'))


@app.route('/toggle_registration', methods=['POST'])
@login_required
def toggle_registration():
    # Ensure the logged-in user is an admin
    username = session.get('active_user')

    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    user = next((u for u in users if u['username'] == username), None)
    if user and user['kind'] == 'admin':
        allow_registration = 'allow_registration' in request.form

        # Update the config file
        config_file = os.path.join(DATA_DIR, 'config.json')
        config = {'allow_registration': allow_registration}
        with open(config_file, 'w') as f:
            json.dump(config, f)

        flash("Settings updated successfully.", "success")
        return redirect(url_for('admin_area'))

    flash("You do not have permission to perform this action.", "danger")
    return redirect(url_for('home'))

if __name__ == '__main__':
    print("Loading config file from:", USERS_FILE)
    app.run(debug=True)
