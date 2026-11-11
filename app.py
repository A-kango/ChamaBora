import os
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chamabora-local-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'https://ep-orange-bonus-b4ogtvyg.apirest.c-6.us-east-2.aws.neon.tech/neondb/rest/v1'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'treasurer', 'secretary', 'member', or 'advisor'
    
    # Chama association
    chama_name = db.Column(db.String(150), nullable=True)
    contributions = db.relationship('Contribution', backref='member', lazy=True, cascade='all, delete-orphan')
    
    # Advisor specific fields
    profession = db.Column(db.String(150), nullable=True)
    hourly_rate = db.Column(db.Float, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    
    # Advisor bookings relationship with explicit foreign keys
    advisor_bookings = db.relationship('Booking', foreign_keys='Booking.advisor_id', backref='advisor_profile', lazy=True, cascade='all, delete-orphan')

class Contribution(db.Model):
    __tablename__ = 'contributions'
    id = db.Column(db.Integer, primary_key=True)
    chama_name = db.Column(db.String(150), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_code = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.String(50), nullable=False)

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    chama_name = db.Column(db.String(150), nullable=False)
    advisor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    service_type = db.Column(db.String(150), nullable=False)
    google_meet_link = db.Column(db.String(300), nullable=True) # Google Meet link inputed by secretary/treasurer
    status = db.Column(db.String(50), default='Confirmed')
    date = db.Column(db.String(50), nullable=False)

with app.app_context():
    db.create_all()

# HTML Templates with Tailwind CSS
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChamaBora Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-gray-50 text-gray-900 font-sans antialiased">
    <nav class="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center shadow-xs">
        <div class="flex items-center space-x-3">
            <div class="w-10 h-10 rounded-xl bg-emerald-600 flex items-center justify-center text-white font-bold">
                <i class="fa-solid fa-shield-halved"></i>
            </div>
            <span class="text-xl font-black text-gray-900">Chama<span class="text-emerald-600">Bora</span></span>
        </div>
        <div class="space-x-4">
            <a href="/advisors" class="text-sm font-semibold text-gray-700 hover:text-emerald-600">Advisor Hub</a>
            {% if 'user_id' in session %}
                <a href="/dashboard" class="text-sm font-semibold text-gray-700 hover:text-emerald-600">Dashboard</a>
                <a href="/logout" class="px-4 py-2 text-sm font-bold text-white bg-red-600 hover:bg-red-700 rounded-xl">Logout</a>
            {% else %}
                <a href="/login" class="text-sm font-semibold text-gray-700 hover:text-emerald-600">Login</a>
                <a href="/signup" class="px-4 py-2 text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl">Get Started</a>
            {% endif %}
        </div>
    </nav>
    <div class="container mx-auto px-4 py-8">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="mb-6 p-4 rounded-xl text-sm font-semibold {% if category == 'error' %}bg-red-100 text-red-700 border border-red-200{% else %}bg-emerald-100 text-emerald-700 border border-emerald-200{% endif %}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {{ content | safe }}
    </div>
</body>
</html>
"""

SIGNUP_HTML = """
<div class="max-w-md mx-auto bg-white p-8 rounded-3xl border border-gray-200 shadow-xl mt-6">
    <h2 class="text-2xl font-black text-gray-900 mb-2">Create ChamaBora Account</h2>
    <p class="text-xs text-gray-500 mb-6">Register as Treasurer, Secretary, Member, or Financial Advisor.</p>
    <form method="POST" class="space-y-4" onsubmit="toggleFields()">
        <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1">Account Role</label>
            <select name="role" id="roleSelect" onchange="toggleFields()" class="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-emerald-500 text-sm bg-white">
                <option value="treasurer">Chama Treasurer / Admin</option>
                <option value="secretary">Chama Secretary</option>
                <option value="member">Chama Member</option>
                <option value="advisor">Financial Advisor / Expert</option>
            </select>
        </div>
        <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1">Full Name</label>
            <input type="text" name="name" required placeholder="Jane Wanjiku" class="w-full px-4 py-3 rounded-xl border border-gray-300 text-sm">
        </div>
        <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1">Username (For Login)</label>
            <input type="text" name="username" required placeholder="jane_wanjiku" class="w-full px-4 py-3 rounded-xl border border-gray-300 text-sm">
        </div>
        
        <div id="chamaField">
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1">Chama Name</label>
            <input type="text" name="chama_name" placeholder="Umoja Investment Group" class="w-full px-4 py-3 rounded-xl border border-gray-300 text-sm">
        </div>

        <div id="advisorFields" style="display:none;" class="space-y-4">
            <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1">Profession / Specialty</label>
                <input type="text" name="profession" placeholder="Certified Land Surveyor" class="w-full px-4 py-3 rounded-xl border border-gray-300 text-sm">
            </div>
            <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1">Hourly Rate (KSh)</label>
                <input type="number" name="hourly_rate" placeholder="5000" class="w-full px-4 py-3 rounded-xl border border-gray-300 text-sm">
            </div>
            <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1">Bio</label>
                <textarea name="bio" placeholder="Experienced land advocate..." class="w-full px-4 py-3 rounded-xl border border-gray-300 text-sm"></textarea>
            </div>
        </div>

        <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1">Password</label>
            <input type="password" name="password" required placeholder="••••••••" class="w-full px-4 py-3 rounded-xl border border-gray-300 text-sm">
        </div>
        <button type="submit" class="w-full py-3.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-lg transition text-sm">Register Account</button>
    </form>
    <script>
    function toggleFields() {
        var role = document.getElementById('roleSelect').value;
        if(role === 'advisor') {
            document.getElementById('chamaField').style.display = 'none';
            document.getElementById('advisorFields').style.display = 'block';
        } else {
            document.getElementById('chamaField').style.display = 'block';
            document.getElementById('advisorFields').style.display = 'none';
        }
    }
    </script>
</div>
"""

LOGIN_HTML = """
<div class="max-w-md mx-auto bg-white p-8 rounded-3xl border border-gray-200 shadow-xl mt-10">
    <h2 class="text-2xl font-black text-gray-900 mb-2">Welcome Back</h2>
    <p class="text-xs text-gray-500 mb-6">Sign in using your username and password.</p>
    <form method="POST" class="space-y-4">
        <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1">Username</label>
            <input type="text" name="username" required placeholder="jane_wanjiku" class="w-full px-4 py-3 rounded-xl border border-gray-300 text-sm">
        </div>
        <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-gray-600 mb-1">Password</label>
            <input type="password" name="password" required placeholder="••••••••" class="w-full px-4 py-3 rounded-xl border border-gray-300 text-sm">
        </div>
        <button type="submit" class="w-full py-3.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-lg transition text-sm">Login</button>
    </form>
    <p class="text-xs text-center text-gray-500 mt-6">Don't have an account? <a href="/signup" class="text-emerald-600 font-bold hover:underline">Sign up</a></p>
</div>
"""

ADMIN_DASHBOARD_HTML = """
<div class="max-w-6xl mx-auto space-y-8">
    <div class="bg-gradient-to-r from-gray-900 to-gray-800 text-white p-8 rounded-3xl shadow-xl flex justify-between items-center">
        <div>
            <span class="px-3 py-1 bg-emerald-500/20 text-emerald-400 text-xs font-bold uppercase rounded-full">{{ role_title }} Portal</span>
            <h1 class="text-3xl font-black mt-2">{{ user.chama_name }}</h1>
            <p class="text-xs text-gray-400 mt-1">{{ role_title }}: {{ user.name }} (@{{ user.username }})</p>
        </div>
        <div class="flex items-center gap-4">
            <a href="/advisors" class="px-5 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-sm shadow-md transition"><i class="fa-solid fa-handshake-angle mr-2"></i>Browse & Book Advisor Hub</a>
            <div class="bg-white/10 px-6 py-4 rounded-2xl border border-white/10 text-right">
                <p class="text-xs text-gray-400">Total Group Vault Balance</p>
                <p class="text-3xl font-black text-emerald-400">KSh {{ "%.2f"|format(total_balance) }}</p>
            </div>
        </div>
    </div>

    <div class="grid md:grid-cols-3 gap-8">
        <div class="bg-white p-6 rounded-3xl border border-gray-200 shadow-sm md:col-span-1">
            <h3 class="text-lg font-bold text-gray-900 mb-2"><i class="fa-solid fa-receipt text-emerald-600 mr-2"></i>Record Member Payment</h3>
            <p class="text-xs text-gray-500 mb-4">Select member and record contribution receipt.</p>
            <form method="POST" action="/add_contribution" class="space-y-4">
                <div>
                    <label class="block text-xs font-bold uppercase text-gray-600 mb-1">Select Member</label>
                    <select name="member_id" required class="w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm bg-white">
                        {% for m in members %}
                        <option value="{{ m.id }}">{{ m.name }} (@{{ m.username }})</option>
                        {% endfor %}
                    </select>
                </div>
                <div>
                    <label class="block text-xs font-bold uppercase text-gray-600 mb-1">Amount (KSh)</label>
                    <input type="number" step="0.01" name="amount" required placeholder="5000" class="w-full px-4 py-2.5 rounded-xl border border-gray-300 text-sm">
                </div>
                <div>
                    <label class="block text-xs font-bold uppercase text-gray-600 mb-1">M-Pesa Transaction Code</label>
                    <input type="text" name="transaction_code" required placeholder="RGH789XYZ" class="w-full px-4 py-3 rounded-xl border border-gray-300 text-sm uppercase">
                </div>
                <button type="submit" class="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-sm">Record Contribution</button>
            </form>
        </div>

        <div class="bg-white p-6 rounded-3xl border border-gray-200 shadow-sm md:col-span-2">
            <h3 class="text-lg font-bold text-gray-900 mb-4"><i class="fa-solid fa-wallet text-blue-600 mr-2"></i>{{ user.chama_name }} Ledger</h3>
            <table class="w-full text-left text-sm text-gray-600">
                <thead class="bg-gray-50 text-xs uppercase text-gray-500 border-b">
                    <tr>
                        <th class="py-3 px-4">Member</th>
                        <th class="py-3 px-4">Receipt Code</th>
                        <th class="py-3 px-4">Date</th>
                        <th class="py-3 px-4 text-right">Amount</th>
                    </tr>
                </thead>
                <tbody class="divide-y">
                    {% for c in contributions %}
                    <tr>
                        <td class="py-3 px-4 font-bold text-gray-900">{{ c.member.name }}</td>
                        <td class="py-3 px-4 font-mono text-xs text-emerald-600 font-bold">{{ c.transaction_code }}</td>
                        <td class="py-3 px-4 text-xs text-gray-400">{{ c.date }}</td>
                        <td class="py-3 px-4 text-right font-extrabold text-gray-900">+KSh {{ "%.2f"|format(c.amount) }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="4" class="text-center py-8 text-gray-400 italic">No contributions recorded yet.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
"""

MEMBER_DASHBOARD_HTML = """
<div class="max-w-5xl mx-auto space-y-8">
    <div class="bg-gradient-to-r from-emerald-900 to-teal-900 text-white p-8 rounded-3xl shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
            <span class="px-3 py-1 bg-white/20 text-emerald-200 text-xs font-bold uppercase rounded-full">Member Portal</span>
            <h1 class="text-3xl font-black mt-2">{{ user.chama_name }}</h1>
            <p class="text-xs text-emerald-200 mt-1">Logged in as: <strong class="text-white">{{ user.name }}</strong> (@{{ user.username }})</p>
        </div>
        <div class="flex gap-4">
            <div class="bg-white/10 px-5 py-4 rounded-2xl border border-white/10 text-right">
                <p class="text-xs text-emerald-200">Group Vault Total</p>
                <p class="text-2xl font-black text-white">KSh {{ "%.2f"|format(total_vault_balance) }}</p>
            </div>
            <div class="bg-white/10 px-5 py-4 rounded-2xl border border-white/10 text-right">
                <p class="text-xs text-emerald-200">My Ownership Share</p>
                <p class="text-2xl font-black text-emerald-400">{{ "%.1f"|format(ownership_share) }}%</p>
            </div>
        </div>
    </div>

    <!-- Booked Advisor Sessions & Google Meet Links -->
    <div class="bg-white p-6 rounded-3xl border border-gray-200 shadow-sm">
        <h3 class="text-lg font-bold text-gray-900 mb-4"><i class="fa-solid fa-video text-blue-600 mr-2"></i>Scheduled Professional Consultations & Google Meet Links</h3>
        <table class="w-full text-left text-sm text-gray-600">
            <thead class="bg-gray-50 text-xs uppercase text-gray-500 border-b">
                <tr>
                    <th class="py-3 px-4">Advisor Name & Specialty</th>
                    <th class="py-3 px-4">Service Required</th>
                    <th class="py-3 px-4">Booking Time</th>
                    <th class="py-3 px-4 text-right">Google Meet Link</th>
                </tr>
            </thead>
            <tbody class="divide-y">
                {% for b in chama_bookings %}
                <tr>
                    <td class="py-3 px-4 font-bold text-gray-900">
                        {{ b.advisor_profile.name }} <span class="block text-xs font-normal text-gray-500">{{ b.advisor_profile.profession }}</span>
                    </td>
                    <td class="py-3 px-4 text-gray-700">{{ b.service_type }}</td>
                    <td class="py-3 px-4 text-xs text-gray-400">{{ b.date }}</td>
                    <td class="py-3 px-4 text-right">
                        {% if b.google_meet_link %}
                        <a href="{{ b.google_meet_link }}" target="_blank" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl inline-flex items-center space-x-1 transition shadow-sm">
                            <i class="fa-solid fa-video mr-1"></i><span>Join Meet</span>
                        </a>
                        {% else %}
                        <span class="text-xs text-gray-400 italic">No link provided</span>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="4" class="text-center py-8 text-gray-400 italic">No advisor sessions booked for your Chama yet.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- Personal Contributions Summary -->
    <div class="bg-white p-6 rounded-3xl border border-gray-200 shadow-sm">
        <h3 class="text-lg font-bold text-gray-900 mb-4"><i class="fa-solid fa-user-check text-emerald-600 mr-2"></i>My Personal Contributions (Total: KSh {{ "%.2f"|format(my_total_contributions) }})</h3>
        <table class="w-full text-left text-sm text-gray-600">
            <thead class="bg-gray-50 text-xs uppercase text-gray-500 border-b">
                <tr>
                    <th class="py-3 px-4">Receipt Code</th>
                    <th class="py-3 px-4">Date Recorded</th>
                    <th class="py-3 px-4 text-right">Amount</th>
                </tr>
            </thead>
            <tbody class="divide-y">
                {% for c in my_contributions %}
                <tr>
                    <td class="py-3 px-4 font-mono text-xs text-emerald-600 font-bold">{{ c.transaction_code }}</td>
                    <td class="py-3 px-4 text-xs text-gray-400">{{ c.date }}</td>
                    <td class="py-3 px-4 text-right font-extrabold text-gray-900">+KSh {{ "%.2f"|format(c.amount) }}</td>
                </tr>
                {% else %}
                <tr><td colspan="3" class="text-center py-8 text-gray-400 italic">No personal contributions recorded yet.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

ADVISOR_DASHBOARD_HTML = """
<div class="max-w-5xl mx-auto space-y-8">
    <div class="bg-gradient-to-r from-blue-900 to-indigo-900 text-white p-8 rounded-3xl shadow-xl flex justify-between items-center">
        <div>
            <span class="px-3 py-1 bg-blue-500/20 text-blue-300 text-xs font-bold uppercase rounded-full">Advisor Hub Profile</span>
            <h1 class="text-3xl font-black mt-2">{{ user.name }}</h1>
            <p class="text-xs text-blue-200 mt-1">{{ user.profession }} • KSh {{ user.hourly_rate }}/hr</p>
        </div>
        <div class="bg-white/10 px-6 py-4 rounded-2xl border border-white/10 text-right">
            <p class="text-xs text-blue-200">Consultation Rate</p>
            <p class="text-2xl font-black text-white">KSh {{ user.hourly_rate }}</p>
        </div>
    </div>
    <div class="bg-white p-6 rounded-3xl border border-gray-200 shadow-sm">
        <h3 class="text-lg font-bold text-gray-900 mb-4"><i class="fa-solid fa-calendar-check text-blue-600 mr-2"></i>Chama Consultation Requests & Google Meet Links</h3>
        <table class="w-full text-left text-sm text-gray-600">
            <thead class="bg-gray-50 text-xs uppercase text-gray-500 border-b">
                <tr>
                    <th class="py-3 px-4">Chama Name</th>
                    <th class="py-3 px-4">Service Required</th>
                    <th class="py-3 px-4">Booking Time</th>
                    <th class="py-3 px-4 text-right">Google Meet Link</th>
                </tr>
            </thead>
            <tbody class="divide-y">
                {% for b in bookings %}
                <tr>
                    <td class="py-3 px-4 font-bold text-gray-900">{{ b.chama_name }}</td>
                    <td class="py-3 px-4 text-gray-700">{{ b.service_type }}</td>
                    <td class="py-3 px-4 text-xs text-gray-400">{{ b.date }}</td>
                    <td class="py-3 px-4 text-right">
                        {% if b.google_meet_link %}
                        <a href="{{ b.google_meet_link }}" target="_blank" class="text-blue-600 font-bold hover:underline text-xs">Open Meet Link</a>
                        {% else %}
                        <span class="text-xs text-gray-400">None</span>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr><td colspan="4" class="text-center py-8 text-gray-400 italic">No consultation bookings from chamas yet.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""

ADVISOR_HUB_HTML = """
<div class="max-w-6xl mx-auto space-y-8">
    <div class="text-center max-w-2xl mx-auto">
        <h1 class="text-3xl font-black text-gray-900">ChamaBora Advisor Hub</h1>
        <p class="text-gray-600 text-sm mt-2">Connect your investment group with verified land surveyors, financial planners, and legal advocates.</p>
    </div>
    <div class="grid md:grid-cols-3 gap-6">
        {% for adv in advisors %}
        <div class="bg-white p-6 rounded-3xl border border-gray-200 shadow-sm flex flex-col justify-between">
            <div>
                <span class="text-xs font-bold uppercase tracking-wider text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full">{{ adv.profession }}</span>
                <h3 class="text-xl font-bold text-gray-900 mt-4">{{ adv.name }}</h3>
                <p class="text-xs text-gray-500 mt-1 mb-4">{{ adv.bio }}</p>
                <p class="text-sm font-black text-gray-900 mb-4">Rate: KSh {{ adv.hourly_rate }} / hr</p>
            </div>
            
            {% if session.get('user_id') and session.get('role') in ['treasurer', 'secretary'] %}
            <form method="POST" action="/book_advisor/{{ adv.id }}" class="space-y-3 pt-4 border-t">
                <input type="text" name="service_type" required placeholder="e.g. Ruiru Land Due Diligence" class="w-full px-3 py-2 text-xs rounded-xl border border-gray-300">
                <input type="url" name="google_meet_link" required placeholder="Google Meet Link (https://meet.google.com/...)" class="w-full px-3 py-2 text-xs rounded-xl border border-gray-300">
                <button type="submit" class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl transition">Book Advisor & Set Meet Link</button>
            </form>
            {% else %}
            <a href="/login" class="mt-4 w-full py-2.5 bg-gray-900 hover:bg-emerald-600 text-white font-bold text-center rounded-xl transition text-xs">Login as Treasurer/Secretary to Book</a>
            {% endif %}
        </div>
        {% else %}
        <p class="text-center text-gray-400 col-span-3 py-12">No advisors registered yet.</p>
        {% endfor %}
    </div>
</div>
"""

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('advisors'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        role = request.form.get('role')
        name = request.form.get('name')
        username = request.form.get('username').strip().lower()
        password = request.form.get('password')
        
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash('Username already taken.', 'error')
            return redirect(url_for('signup'))
        
        hashed = generate_password_hash(password)
        
        if role == 'advisor':
            profession = request.form.get('profession')
            hourly_rate = float(request.form.get('hourly_rate') or 0.0)
            bio = request.form.get('bio')
            new_user = User(name=name, username=username, password=hashed, role='advisor', profession=profession, hourly_rate=hourly_rate, bio=bio)
        else:
            chama_name = request.form.get('chama_name').strip()
            new_user = User(name=name, username=username, password=hashed, role=role, chama_name=chama_name)
            
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template_string(BASE_HTML, content=SIGNUP_HTML)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip().lower()
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template_string(BASE_HTML, content=LOGIN_HTML)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login.', 'error')
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    
    if user.role == 'advisor':
        bookings = Booking.query.filter_by(advisor_id=user.id).order_by(Booking.id.desc()).all()
        return render_template_string(BASE_HTML, content=render_template_string(ADVISOR_DASHBOARD_HTML, user=user, bookings=bookings))
    
    elif user.role in ['treasurer', 'secretary']:
        role_title = 'Treasurer' if user.role == 'treasurer' else 'Secretary'
        contributions = Contribution.query.filter_by(chama_name=user.chama_name).order_by(Contribution.id.desc()).all()
        members = User.query.filter_by(role='member', chama_name=user.chama_name).all()
        total_balance = sum(c.amount for c in contributions)
        return render_template_string(BASE_HTML, content=render_template_string(ADMIN_DASHBOARD_HTML, user=user, role_title=role_title, contributions=contributions, members=members, total_balance=total_balance))
    
    else: # Member
        all_chama_contributions = Contribution.query.filter_by(chama_name=user.chama_name).all()
        total_vault_balance = sum(c.amount for c in all_chama_contributions)
        my_contributions = [c for c in all_chama_contributions if c.user_id == user.id]
        my_total_contributions = sum(c.amount for c in my_contributions)
        ownership_share = (my_total_contributions / total_vault_balance * 100) if total_vault_balance > 0 else 0.0
        
        # Broadcast all bookings for this Chama to the member dashboard
        chama_bookings = Booking.query.filter_by(chama_name=user.chama_name).order_by(Booking.id.desc()).all()
        
        return render_template_string(BASE_HTML, content=render_template_string(MEMBER_DASHBOARD_HTML, user=user, total_vault_balance=total_vault_balance, my_total_contributions=my_total_contributions, my_contributions=my_contributions, ownership_share=ownership_share, chama_bookings=chama_bookings))

@app.route('/advisors')
def advisors():
    advisors_list = User.query.filter_by(role='advisor').all()
    return render_template_string(BASE_HTML, content=render_template_string(ADVISOR_HUB_HTML, advisors=advisors_list))

@app.route('/book_advisor/<int:advisor_id>', methods=['POST'])
def book_advisor(advisor_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.role not in ['treasurer', 'secretary']:
        flash('Only treasurers and secretaries can book advisors for the group.', 'error')
        return redirect(url_for('advisors'))
        
    service_type = request.form.get('service_type')
    google_meet_link = request.form.get('google_meet_link')
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    new_booking = Booking(
        chama_name=user.chama_name, 
        advisor_id=advisor_id, 
        service_type=service_type, 
        google_meet_link=google_meet_link,
        date=date_str, 
        status='Confirmed'
    )
    db.session.add(new_booking)
    db.session.commit()
    
    flash('Advisor booked successfully! Google Meet link broadcasted to all chama members.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/add_contribution', methods=['POST'])
def add_contribution():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.role not in ['treasurer', 'secretary']:
        flash('Only treasurers and secretaries can record contributions.', 'error')
        return redirect(url_for('dashboard'))
        
    member_id = request.form.get('member_id')
    amount = request.form.get('amount')
    code = request.form.get('transaction_code').upper()
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    if Contribution.query.filter_by(transaction_code=code).first():
        flash('Transaction code already exists!', 'error')
        return redirect(url_for('dashboard'))
        
    try:
        new_c = Contribution(chama_name=user.chama_name, user_id=int(member_id), amount=float(amount), transaction_code=code, date=date_str)
        db.session.add(new_c)
        db.session.commit()
        flash('Contribution recorded successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error recording payment.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
