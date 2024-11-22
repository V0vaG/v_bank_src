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

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump([], f)


@app.route('/register', methods=['GET', 'POST'])
def register():
    users_file = os.path.join(DATA_DIR, 'users.json')

    # Load existing users
    if os.path.exists(users_file):
        with open(users_file, 'r') as f:
            users = json.load(f)
    else:
        users = []

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role') if 'role' in request.form else 'user'

        # Check if username already exists
        if any(user['username'] == username for user in users):
            flash(f"Username '{username}' already exists.", "danger")
            return redirect(url_for('register'))

        # Hash the password before saving it
        hashed_password = generate_password_hash(password)

        # Create a new user object
        new_user = {
            'username': username,
            'password': hashed_password,
            'kind': role  # 'admin' or 'user'
        }

        # If the role is 'user', include additional fields
        if role == 'user':
            name = request.form.get('name')
            birthday = request.form.get('birthday')  # New field
            balance = request.form.get('balance', 0)  # Default to 0
            sellery = request.form.get('sellery', 0)  # Default to 0
            interest = request.form.get('interest', 0)  # Default to 0
            overdraft = request.form.get('overdraft', 0)  # Default to 0

            # Add additional fields to the user object
            new_user.update({
                'name': name,
                'birthday': birthday,
                'balance': int(balance),
                'sellery': int(sellery),
                'interest': int(interest),
                'overdraft': int(overdraft)
            })

        # Save the new user to the list
        users.append(new_user)
        with open(users_file, 'w') as f:
            json.dump(users, f, indent=4)

        flash(f"User created successfully as {role}!", "success")
        return redirect(url_for('show_login'))

    # Check if accessed from admin area or login page
    show_role_selection = 'admin_area' in request.args  # Flag for role dropdown
    back_url = url_for('admin_area') if 'admin_area' in request.args else url_for('show_login')  # Determine where to go back to

    return render_template('register.html', show_role_selection=show_role_selection, back_url=back_url)


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    # Load users
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
    else:
        users = []

    # Find the user by username
    user = next((u for u in users if u['username'] == username), None)

    # Check if the user exists and password matches
    if user and check_password_hash(user['password'], password):
        session['active_user'] = username  # Store the username in the session
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
    # Load the logged-in user's information
    username = session.get('active_user')

    # Load users data
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    # Find the current user
    user = next((u for u in users if u['username'] == username), None)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('show_login'))

    # Handle "Get Money" form submission
    if request.method == 'POST':
        try:
            amount = int(request.form.get('amount', 0))
            if amount <= 0:
                flash("Enter a positive amount.", "danger")
            elif user['balance'] < amount:
                flash("Insufficient balance.", "danger")
            else:
                user['balance'] -= amount
                # Save updated users data
                with open(USERS_FILE, 'w') as f:
                    json.dump(users, f, indent=4)
                flash(f"${amount} withdrawn successfully!", "success")
        except ValueError:
            flash("Invalid amount entered.", "danger")

    # Determine if the current user is an admin
    is_admin = user['kind'] == 'admin'

    # Pass the current year to the template
    current_year = datetime.now().year

    return render_template(
        'index.html',
        version=version,
        host=host,
        is_admin=is_admin,
        user=user,
        current_year=current_year
    )

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_area():
    # Ensure the logged-in user is an admin
    username = session.get('active_user')

    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    user = next((u for u in users if u['username'] == username), None)
    if user and user['kind'] == 'admin':
        # Load the external registration setting
        config_file = os.path.join(DATA_DIR, 'config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {"allow_registration": False}

        allow_registration = config.get('allow_registration', False)

        # Pass the users' data to the template
        return render_template('admin.html', allow_registration=allow_registration, user_data=users)
    
    flash("You do not have access to the admin area.", "danger")
    return redirect(url_for('home'))

@app.route('/edit_user/<username>', methods=['GET', 'POST'])
@login_required
def edit_user(username):
    # Ensure the logged-in user is an admin
    active_username = session.get('active_user')
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    active_user = next((u for u in users if u['username'] == active_username), None)
    if not active_user or active_user['kind'] != 'admin':
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('home'))

    # Find the user to edit
    user = next((u for u in users if u['username'] == username), None)
    if not user:
        flash(f"User '{username}' not found.", "danger")
        return redirect(url_for('admin_area'))

    if request.method == 'POST':
        # Update user details
        user['name'] = request.form.get('name')
        user['username'] = request.form.get('username')
        user['birthday'] = request.form.get('birthday')
        user['balance'] = int(request.form.get('balance', 0))
        user['sellery'] = int(request.form.get('sellery', 0))
        user['interest'] = int(request.form.get('interest', 0))
        user['overdraft'] = int(request.form.get('overdraft', 0))
        user['kind'] = request.form.get('role')  # Update role

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

    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    # Check if the current user is an admin
    active_user = next((u for u in users if u['username'] == active_username), None)
    if not active_user or active_user['kind'] != 'admin':
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('home'))

    # Prevent the admin from deleting themselves
    if active_username == username:
        flash("You cannot delete yourself.", "danger")
        return redirect(url_for('admin_area'))

    # Filter out the user to be deleted
    updated_users = [user for user in users if user['username'] != username]

    # Save the updated user list
    with open(USERS_FILE, 'w') as f:
        json.dump(updated_users, f, indent=4)

    flash(f"User '{username}' has been deleted.", "success")
    return redirect(url_for('admin_area'))

@app.route('/adjust_balance/<username>', methods=['POST'])
@login_required
def adjust_balance(username):
    # Ensure the logged-in user is an admin
    active_username = session.get('active_user')

    with open(USERS_FILE, 'r') as f:
        users = json.load(f)

    active_user = next((u for u in users if u['username'] == active_username), None)
    if not active_user or active_user['kind'] != 'admin':
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('admin_area'))

    # Find the user to adjust
    user = next((u for u in users if u['username'] == username), None)
    if not user:
        flash(f"User '{username}' not found.", "danger")
        return redirect(url_for('admin_area'))

    # Adjust the user's balance
    try:
        amount = int(request.form.get('amount'))
        user['balance'] += amount

        # Save updated users list
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=4)

        flash(f"User '{username}' balance updated by {amount}.", "success")
    except ValueError:
        flash("Invalid amount entered.", "danger")

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
