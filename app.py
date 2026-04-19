from flask import Flask, render_template, request, redirect, session, jsonify
from datetime import datetime, timedelta
import json
import os
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

ET = pytz.timezone('US/Eastern')
def now_et():
    return datetime.now(ET)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

DATA_FILE = 'patients.json'

# Email configuration (update with your SMTP settings)
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'your-email@gmail.com',  # Update this
    'sender_password': 'your-app-password',   # Update this (use app password for Gmail)
}

def send_verification_code(email):
    """Send a 6-digit verification code to the email"""
    code = str(random.randint(100000, 999999))
    try:
        msg = MIMEText(f'Your Puff & Glow verification code is: {code}')
        msg['Subject'] = '🫁 Puff & Glow - Email Verification'
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = email
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
        return code
    except Exception as e:
        print(f"Email verification error: {e}")
        print(f"[TEST] Verification code for {email}: {code}")
        return code  # Still return code for testing even if email fails

def send_email_reminder(recipient_email, patient_name, reminders):
    """Send daily reminder email to patient"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🫁 Puff & Glow - Your Daily Reminders'
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = recipient_email
        
        # Create email body
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #667eea;">🫁✨ Puff & Glow Daily Reminder</h2>
            <p>Hi {patient_name},</p>
            <p>Here are your reminders for today:</p>
            
            <h3 style="color: #667eea;">💉 Vaccines</h3>
            <ul>
                {''.join([f'<li>{v}</li>' for v in reminders.get('vaccines', [])]) or '<li>No vaccines due</li>'}
            </ul>
            
            <h3 style="color: #667eea;">🩺 Lab Work</h3>
            <ul>
                {''.join([f'<li>{l}</li>' for l in reminders.get('labwork', [])[-3:]]) or '<li>No lab work scheduled</li>'}
            </ul>
            
            <h3 style="color: #667eea;">💪 Exercise</h3>
            <ul>
                {''.join([f'<li>{e}</li>' for e in reminders.get('exercise', [])[-2:]]) or '<li>Rest and gentle movement</li>'}
            </ul>
            
            <p style="margin-top: 20px;">Take care! 💜</p>
            <p><a href="http://localhost:5000" style="color: #667eea;">Visit Puff & Glow</a></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_daily_reminders():
    """Check all patients and send reminders at their preferred time"""
    patients = load_patients()
    current_time = now_et().strftime('%H:%M')
    
    for username, patient in patients.items():
        if patient.get('email') and patient.get('reminder_time') and patient.get('pregnancy_week'):
            # Check if it's time to send reminder
            if patient['reminder_time'] == current_time:
                reminders = get_reminders(patient['pregnancy_week'])
                send_email_reminder(patient['email'], username, reminders)

def auto_update_pregnancy_week(patient):
    """Automatically update pregnancy week based on initial set date"""
    if not patient.get('pregnancy_week'):
        return
    
    if 'week_set_date' not in patient:
        # First time - set the date
        patient['week_set_date'] = now_et().strftime('%Y-%m-%d')
        return
    
    try:
        set_date = datetime.strptime(patient['week_set_date'], '%Y-%m-%d')
        weeks_passed = (now_et() - set_date).days // 7
        
        if weeks_passed > 0:
            new_week = patient['pregnancy_week'] + weeks_passed
            if new_week <= 42:  # Cap at 42 weeks
                patient['pregnancy_week'] = new_week
                patient['week_set_date'] = now_et().strftime('%Y-%m-%d')
    except:
        pass

def load_patients():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_patients(patients):
    with open(DATA_FILE, 'w') as f:
        json.dump(patients, f, indent=2)

def get_vaccine_info():
    return {
        "Tdap (27-36 weeks)": {
            "benefit": "Protects baby from whooping cough in first months of life",
            "reminder": "Schedule with your OB/GYN between weeks 27-36"
        },
        "RSV (32-36 weeks)": {
            "benefit": "Protects newborn from respiratory syncytial virus",
            "reminder": "Schedule with your OB/GYN between weeks 32-36"
        },
        "COVID-19": {
            "benefit": "Reduces risk of severe illness and protects baby",
            "reminder": "Can be given at any time during pregnancy - schedule with provider"
        },
        "Flu (seasonal)": {
            "benefit": "Prevents influenza complications during pregnancy",
            "reminder": "Schedule during flu season (October-March)"
        },
        "Hepatitis A": {
            "benefit": "Protects against liver infection if at risk",
            "reminder": "Discuss with provider if you have risk factors"
        },
        "Pneumococcal (if chronic lung condition)": {
            "benefit": "Prevents pneumonia complications with pulmonary hypertension",
            "reminder": "Schedule with pulmonologist or OB/GYN if you have chronic lung disease"
        }
    }

def get_reminders(week):
    reminders = {
        8: {"vaccines": [], "labwork": ["First prenatal visit", "Blood type and Rh", "Complete blood count", "Echocardiogram baseline"], "management": ["Start prenatal vitamins", "Monitor oxygen saturation"], "exercise": ["Light walking 10-15 min with rest breaks"]},
        12: {"vaccines": [], "labwork": ["Genetic screening", "Ultrasound", "Pulmonary function test"], "management": ["Continue prenatal vitamins", "Track shortness of breath"], "exercise": ["Gentle walking, avoid overexertion"]},
        16: {"vaccines": [], "labwork": ["Amniocentesis (if needed)"], "management": ["Monitor weight gain", "Watch for swelling"], "exercise": ["Short walks with frequent rest"]},
        20: {"vaccines": [], "labwork": ["Anatomy ultrasound", "Echocardiogram follow-up"], "management": ["Track fetal movement", "Monitor blood pressure"], "exercise": ["Light activity as tolerated"]},
        24: {"vaccines": [], "labwork": ["Glucose screening"], "management": ["Monitor blood pressure", "Watch for chest discomfort"], "exercise": ["Breathing exercises, light stretching"]},
        27: {"vaccines": ["Tdap (27-36 weeks)", "COVID-19", "Flu (if seasonal)"], "labwork": ["Glucose tolerance test", "Antibody screen"], "management": ["Start kick counts", "Monitor heart rate"], "exercise": ["Gentle breathing exercises"]},
        32: {"vaccines": ["RSV (32-36 weeks)", "Pneumococcal (if chronic lung)"], "labwork": ["Complete blood count", "Echocardiogram"], "management": ["Weekly weight checks", "Daily oxygen monitoring"], "exercise": ["Minimal activity, rest frequently"]},
        36: {"vaccines": [], "labwork": ["Group B strep test"], "management": ["Weekly doctor visits", "Monitor breathing"], "exercise": ["Light walking only, prioritize rest"]},
        38: {"vaccines": [], "labwork": ["Cervical exam"], "management": ["Watch for labor signs", "Keep oxygen nearby"], "exercise": ["Rest and gentle breathing"]}
    }
    
    current_reminders = {"vaccines": [], "labwork": [], "management": [], "exercise": []}
    for w in sorted(reminders.keys()):
        if week >= w:
            for key in current_reminders:
                current_reminders[key].extend(reminders[w][key])
    
    return current_reminders

def get_symptom_management():
    return {
        "Shortness of Breath": ["Rest frequently", "Use pillows to prop up while sleeping", "Avoid lying flat", "Practice slow, deep breathing"],
        "Fatigue": ["Take multiple short rest periods", "Prioritize sleep", "Ask for help with daily tasks", "Conserve energy for essential activities"],
        "Chest Discomfort": ["Rest immediately", "Monitor heart rate", "Contact provider if persistent", "Avoid strenuous activity"],
        "Swelling": ["Elevate feet when resting", "Avoid standing long periods", "Monitor weight daily", "Report sudden swelling to provider"],
        "Dizziness": ["Stand up slowly", "Stay hydrated", "Avoid hot environments", "Sit or lie down if feeling lightheaded"],
        "Rapid Heartbeat": ["Rest and breathe slowly", "Monitor pulse", "Avoid caffeine", "Contact provider if concerning"]
    }

def get_management_visuals():
    return {
        "Lateral Position (3rd Trimester)": {
            "description": "Lie on your left side to minimize compression of the Inferior Vena Cava (IVC). This helps maintain better blood flow to your heart and baby.",
            "icon": "🛏️",
            "image_search": "https://www.google.com/search?q=pregnancy+left+lateral+position&tbm=isch"
        },
        "Elastic Support Stockings": {
            "description": "Wear compression stockings to avoid drastic changes in blood volume. They help prevent blood pooling in your legs and support circulation.",
            "icon": "🧦",
            "image_search": "https://www.google.com/search?q=pregnancy+compression+stockings&tbm=isch"
        }
    }

def get_hospital_portals():
    return [
        {"name": "WellStar Health System", "url": "https://mychart.wellstar.org/MyChart/Authentication/Login?"},
        {"name": "Northside Hospital", "url": "https://myonechart.iqhealth.com/self-enroll/"},
        {"name": "Emory Healthcare", "url": "https://mychart.emoryhealthcare.org/mychart-prd/Authentication/Login?"},
        {"name": "Piedmont Healthcare", "url": "https://mychart.piedmont.org/"}
    ]

def get_hospital_bag_checklist():
    return {
        "For You": ["Insurance cards", "ID", "Birth plan", "Comfortable clothes", "Toiletries", "Phone charger", "Snacks", "Pillow"],
        "For Baby": ["Car seat", "Going home outfit", "Blankets", "Diapers", "Wipes"],
        "Medical": ["Medications list", "Medical records", "Emergency contacts"]
    }

def get_weekly_tips(week):
    tips = {
        8: "Your baby is the size of a raspberry! Focus on staying hydrated and resting.",
        12: "Morning sickness may peak now. Small, frequent meals can help.",
        16: "You might start feeling baby movements soon! Keep monitoring your breathing.",
        20: "Halfway there! Start kick counting when you feel movements.",
        24: "Baby can hear your voice now. Talk and sing to them!",
        27: "Time for Tdap vaccine. Your baby is practicing breathing movements.",
        32: "Baby is gaining weight rapidly. Rest as much as possible.",
        36: "Almost there! Pack your hospital bag and review your birth plan.",
        40: "Full term! Baby could arrive any day. Stay close to home."
    }
    for w in sorted(tips.keys(), reverse=True):
        if week >= w:
            return tips[w]
    return "Welcome to your pregnancy journey!"

def get_faq():
    return [
        {"q": "Can I exercise with pulmonary hypertension?", "a": "Yes, gentle exercise like walking is beneficial. Always follow your doctor's specific recommendations."},
        {"q": "What symptoms should I report immediately?", "a": "Severe shortness of breath, chest pain, rapid heartbeat, or sudden swelling. Call your doctor or 911."},
        {"q": "Is it safe to fly during pregnancy?", "a": "Discuss with your cardiologist. Flying may increase risks with pulmonary hypertension."},
        {"q": "How often should I see my doctor?", "a": "Typically every 2 weeks until week 20, then weekly. Your team may recommend more frequent visits."},
        {"q": "What delivery method is safest?", "a": "Your care team will decide based on your condition. Both vaginal and C-section can be safe with proper planning."}
    ]

def send_emergency_alert(patient_name, emergency_contacts):
    # In production, this would send actual SMS/email
    # For now, we'll create a notification record
    alerts = []
    for contact in emergency_contacts:
        # Only notify if auto_notify is enabled
        if contact.get('auto_notify', False):
            message = f"Hi {contact['name']}, just a quick note from the app. {patient_name} isn't feeling quite like themselves and could use some company. It doesn't seem like an emergency, but it would really help if you could check in on them soon. Your presence always makes a difference."
            alerts.append({
                'contact': contact['name'],
                'phone': contact['phone'],
                'message': message,
                'sent': True
            })
    return alerts

def check_crisis_keywords(message):
    crisis_keywords = [
        'depressed', 'depression', 'suicidal', 'suicide', 'kill myself', 
        'end my life', 'tired to live', 'tired of living', 'want to die',
        'no reason to live', 'better off dead', 'harm myself'
    ]
    message_lower = message.lower()
    for keyword in crisis_keywords:
        if keyword in message_lower:
            return True
    return False

def get_daily_quote():
    quotes = [
        {"text": "You are stronger than you know. One day at a time. 💪", "type": "quote"},
        {"text": "Your body is doing something amazing. Be gentle with yourself. 🌸", "type": "quote"},
        {"text": "Every breath you take is nurturing your baby. You're doing great! 🫁", "type": "quote"},
        {"text": "Rest is not weakness. It's wisdom. 💜", "type": "quote"},
        {"text": "You and your baby are a team. You've got this! 👶", "type": "quote"},
        {"text": "Small steps forward are still progress. Keep going! ✨", "type": "quote"},
        {"text": "Your care team is with you every step of the way. 🩺", "type": "quote"},
        {"text": "Breathe in calm, breathe out worry. You're supported. 🌈", "type": "quote"},
        {"text": "Why did the baby cross the road? To get to the other womb! 😄", "type": "joke"},
        {"text": "What's a pregnant woman's favorite exercise? Baby squats! 🏋️♀️", "type": "joke"},
        {"text": "You're growing a human. That's basically a superpower! 🦸♀️", "type": "quote"},
        {"text": "Remember: You're not just pregnant, you're pre-parent! 👨👩👧", "type": "quote"}
    ]
    from random import choice
    return choice(quotes)
def check_abnormal_values(bp, glucose):
    warnings = []
    classification = "Normal"
    
    # Blood pressure check (systolic/diastolic)
    if bp and '/' in bp:
        try:
            systolic, diastolic = map(int, bp.split('/'))
            if systolic > 140 or diastolic > 90 or systolic < 90 or diastolic < 60:
                warnings.append("blood_pressure")
                classification = "Abnormal"
        except:
            pass
    
    # Glucose check
    if glucose:
        try:
            glucose_val = int(glucose.split()[0])
            if glucose_val > 140 or glucose_val < 60:
                warnings.append("glucose")
                classification = "Abnormal"
        except:
            pass
    
    return warnings, classification

def get_treatment_benefits():
    return [
        "Increases exercise tolerance - helps you do daily activities with less fatigue",
        "Improves pulmonary circulation hemodynamics - makes blood flow easier through your lungs",
        "Reduces strain on your heart - allows your heart to work more efficiently",
        "Helps maintain oxygen levels - ensures you and baby get enough oxygen"
    ]

def get_supplement_info():
    return {
        "Iron": "Prevents anemia and helps carry oxygen in your blood - crucial when your heart is working harder with pulmonary hypertension. Supports increased blood volume during pregnancy.",
        "Folic Acid": "Prevents birth defects and supports red blood cell production. Helps your body manage the extra cardiovascular demands of pregnancy with pulmonary hypertension."
    }

def get_exercise_videos():
    return {
        "Light walking 10-15 min with rest breaks": {
            "video": "https://www.youtube.com/results?search_query=gentle+pregnancy+walking+exercise",
            "image": "🚶‍♀️"
        },
        "Gentle walking, avoid overexertion": {
            "video": "https://www.youtube.com/results?search_query=gentle+pregnancy+walking",
            "image": "🚶‍♀️"
        },
        "Short walks with frequent rest": {
            "video": "https://www.youtube.com/results?search_query=short+pregnancy+walks",
            "image": "🚶‍♀️"
        },
        "Light activity as tolerated": {
            "video": "https://www.youtube.com/results?search_query=light+pregnancy+exercises",
            "image": "🧘‍♀️"
        },
        "Breathing exercises, light stretching": {
            "video": "https://www.youtube.com/results?search_query=pregnancy+breathing+exercises",
            "image": "🫁"
        },
        "Gentle breathing exercises": {
            "video": "https://www.youtube.com/results?search_query=gentle+breathing+exercises+pregnancy",
            "image": "🫁"
        },
        "Minimal activity, rest frequently": {
            "video": "https://www.youtube.com/results?search_query=pregnancy+rest+positions",
            "image": "🛋️"
        },
        "Light walking only, prioritize rest": {
            "video": "https://www.youtube.com/results?search_query=gentle+pregnancy+walking",
            "image": "🚶‍♀️"
        },
        "Rest and gentle breathing": {
            "video": "https://www.youtube.com/results?search_query=pregnancy+breathing+relaxation",
            "image": "🫁"
        }
    }

def get_additional_exercises():
    return {
        "Swimming": {
            "benefit": "Low-impact, supports body weight, reduces joint stress, improves cardiovascular health without overexertion",
            "video": "https://www.youtube.com/results?search_query=pregnancy+swimming+exercises",
            "image": "🏊‍♀️"
        },
        "Stationary Cycling": {
            "benefit": "Helps reduce risk of falling, safe cardiovascular exercise, strengthens legs without impact",
            "video": "https://www.youtube.com/results?search_query=pregnancy+stationary+bike",
            "image": "🚴‍♀️"
        },
        "Light Weights/Resistance": {
            "benefit": "Maintains muscle strength, supports posture, prepares body for labor and recovery",
            "video": "https://www.youtube.com/results?search_query=pregnancy+light+weights+exercises",
            "image": "🏋️‍♀️"
        },
        "Modified Yoga/Pilates": {
            "benefit": "Improves flexibility, reduces stress, strengthens core safely, enhances breathing",
            "video": "https://www.youtube.com/results?search_query=prenatal+yoga+pilates",
            "image": "🧘‍♀️"
        },
        "Pursed Lip Breathing": {
            "benefit": "Slows breathing rate, keeps airways open longer, reduces work of breathing, helps with shortness of breath",
            "video": "https://www.youtube.com/results?search_query=pursed+lip+breathing+technique",
            "image": "😮‍💨"
        },
        "Belly Breathing (Diaphragmatic)": {
            "benefit": "Strengthens diaphragm, increases oxygen intake, reduces stress, improves lung efficiency",
            "video": "https://www.youtube.com/results?search_query=diaphragmatic+breathing+pregnancy",
            "image": "🫁"
        }
    }

def get_exercise_importance():
    return "Exercise during pregnancy with pulmonary hypertension is carefully recommended because it helps maintain cardiovascular fitness, reduces stress on your heart over time, improves circulation, and helps manage weight gain. Gentle, regular movement keeps your body strong for labor and recovery while being mindful of your heart and lung capacity. Always follow your care team's specific guidance."

def get_labwork_explanations():
    return {
        "First prenatal visit": "Establishes baseline health, identifies risk factors, ensures you and baby start pregnancy with optimal care",
        "Blood type and Rh": "Prevents Rh incompatibility issues that could harm baby's blood cells and cause anemia or jaundice",
        "Complete blood count": "Checks for anemia which is crucial - your baby needs adequate oxygen delivery through your blood",
        "Echocardiogram baseline": "Monitors your heart function with pulmonary hypertension to ensure it can handle pregnancy demands",
        "Genetic screening": "Identifies potential genetic conditions early so your team can plan appropriate care for baby",
        "Ultrasound": "Confirms baby's growth, development, and position; checks placenta and amniotic fluid levels",
        "Pulmonary function test": "Assesses your lung capacity to ensure adequate oxygen for you and baby",
        "Amniocentesis (if needed)": "Detects chromosomal abnormalities and genetic disorders to prepare for baby's specific needs",
        "Anatomy ultrasound": "Detailed check of baby's organs, spine, and limbs to detect any developmental concerns early",
        "Echocardiogram follow-up": "Monitors how your heart is adapting to pregnancy's increased demands",
        "Glucose screening": "Detects gestational diabetes which can affect baby's growth and blood sugar at birth",
        "Glucose tolerance test": "Confirms diabetes diagnosis to protect baby from complications like macrosomia or breathing issues",
        "Antibody screen": "Checks for antibodies that could attack baby's blood cells, preventing serious complications",
        "Group B strep test": "Identifies bacteria that could cause serious infection in baby during delivery",
        "Cervical exam": "Checks if your body is preparing for labor and assesses timing for safe delivery"
    }

def convert_to_weeks(trimester=None, month=None):
    if trimester:
        trimester_map = {'1': 8, '2': 20, '3': 32}
        return trimester_map.get(str(trimester), None)
    if month:
        month_map = {'1': 4, '2': 8, '3': 13, '4': 17, '5': 21, '6': 26, '7': 30, '8': 35, '9': 39}
        return month_map.get(str(month), None)
    return None

@app.route('/')
def index():
    if 'username' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/mobile')
def mobile_index():
    if 'username' in session:
        return redirect('/mobile/dashboard')
    return render_template('login.html', mobile=True)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    is_mobile = request.form.get('mobile') == 'true'
    patients = load_patients()
    
    if username in patients and patients[username]['password'] == password:
        session['username'] = username
        if is_mobile:
            return redirect('/mobile/dashboard')
        return redirect('/dashboard')
    return render_template('login.html', error='Invalid credentials', mobile=is_mobile)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        gmail = request.form['gmail']
        recovery = request.form['recovery']
        patients = load_patients()
        
        if username in patients:
            return render_template('register.html', error='Username exists')
        
        # Send verification code
        code = send_verification_code(gmail)
        session['pending_registration'] = {
            'username': username, 'password': password,
            'first_name': first_name, 'last_name': last_name,
            'gmail': gmail, 'recovery': recovery, 'code': code
        }
        return render_template('verify.html', gmail=gmail)
    return render_template('register.html')

@app.route('/verify', methods=['POST'])
def verify():
    pending = session.get('pending_registration')
    if not pending:
        return redirect('/register')
    
    if request.form['code'] != pending['code']:
        return render_template('verify.html', gmail=pending['gmail'], error='Invalid code. Try again.')
    
    patients = load_patients()
    patients[pending['username']] = {
        'password': pending['password'],
        'first_name': pending['first_name'],
        'last_name': pending['last_name'],
        'gmail': pending['gmail'],
        'recovery': pending['recovery'],
        'email_verified': True,
        'registration_date': now_et().strftime('%Y-%m-%d %H:%M:%S'),
        'pregnancy_week': None, 
        'vaccines_received': [],
        'completed_tasks': [],
        'zipcode': '',
        'daily_logs': [],
        'reminder_time': '',
        'clinicians': [],
        'next_appointment': '',
        'trimester': '',
        'month': '',
        'hospital_portal_synced': False,
        'chat_messages': [],
        'emergency_contacts': []
    }
    save_patients(patients)
    session.pop('pending_registration', None)
    session['username'] = pending['username']
    return redirect('/dashboard')

@app.route('/mobile/dashboard')
def mobile_dashboard():
    if 'username' not in session:
        return redirect('/mobile')
    
    patients = load_patients()
    patient = patients.get(session['username'])
    
    if not patient:
        session.pop('username', None)
        return redirect('/mobile')
    
    # Auto-update pregnancy week
    auto_update_pregnancy_week(patient)
    save_patients(patients)
    
    # Initialize missing fields
    if 'vaccines_received' not in patient:
        patient['vaccines_received'] = []
    if 'completed_tasks' not in patient:
        patient['completed_tasks'] = []
    if 'daily_logs' not in patient:
        patient['daily_logs'] = []
    if 'emergency_contacts' not in patient:
        patient['emergency_contacts'] = []
    
    reminders = None
    if patient.get('pregnancy_week'):
        reminders = get_reminders(patient['pregnancy_week'])
    
    return render_template('mobile_dashboard.html', patient=patient, reminders=reminders, 
                         symptoms=get_symptom_management(), vaccine_info=get_vaccine_info(),
                         daily_quote=get_daily_quote(), mobile=True)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/')
    
    patients = load_patients()
    patient = patients.get(session['username'])
    
    if not patient:
        session.pop('username', None)
        return redirect('/')
    
    # Auto-update pregnancy week
    auto_update_pregnancy_week(patient)
    save_patients(patients)
    
    # Initialize missing fields for existing users
    if 'vaccines_received' not in patient:
        patient['vaccines_received'] = []
    if 'vaccines_tracking' not in patient:
        patient['vaccines_tracking'] = {}
    if 'completed_tasks' not in patient:
        patient['completed_tasks'] = []
    if 'tasks_tracking' not in patient:
        patient['tasks_tracking'] = {}
    if 'daily_logs' not in patient:
        patient['daily_logs'] = []
    if 'clinicians' not in patient:
        patient['clinicians'] = []
    if 'chat_messages' not in patient:
        patient['chat_messages'] = []
    if 'emergency_contacts' not in patient:
        patient['emergency_contacts'] = []
    
    reminders = None
    symptoms = get_symptom_management()
    vaccine_info = get_vaccine_info()
    treatment_benefits = get_treatment_benefits()
    supplement_info = get_supplement_info()
    exercise_videos = get_exercise_videos()
    management_visuals = get_management_visuals()
    daily_quote = get_daily_quote()
    additional_exercises = get_additional_exercises()
    exercise_importance = get_exercise_importance()
    labwork_explanations = get_labwork_explanations()
    hospital_portals = get_hospital_portals()
    
    # Calculate countdown for appointment
    appointment_countdown = None
    appointment_status = None
    if patient.get('next_appointment'):
        try:
            appt_date = datetime.strptime(patient['next_appointment'], '%Y-%m-%d').date()
            today_date = now_et().date()
            days_until = (appt_date - today_date).days
            if days_until > 0:
                appointment_countdown = days_until
                appointment_status = "upcoming"
            elif days_until == 0:
                appointment_countdown = 0
                appointment_status = "today"
            else:
                appointment_countdown = abs(days_until)
                appointment_status = "past"
        except:
            pass
    
    # Check vaccine status based on pregnancy week
    all_vaccines_caught_up = False
    if patient.get('pregnancy_week'):
        week = patient['pregnancy_week']
        vaccines_received = patient.get('vaccines_received', [])
        
        # Check if patient has received all vaccines for their trimester
        if week >= 27 and week <= 36:
            required_vaccines = ["Tdap (27-36 weeks)", "COVID-19", "Flu (if seasonal)"]
            if week >= 32:
                required_vaccines.extend(["RSV (32-36 weeks)", "Pneumococcal (if chronic lung)"])
            all_vaccines_caught_up = all(vac in vaccines_received for vac in required_vaccines if "if" not in vac)
        elif week < 27:
            all_vaccines_caught_up = True  # No vaccines due yet
        else:
            all_vaccines_caught_up = True  # Past vaccine window
    
    if patient.get('pregnancy_week'):
        reminders = get_reminders(patient['pregnancy_week'])
        week = patient['pregnancy_week']
        
        # Determine appointment frequency
        if week < 20:
            appointment_frequency = "Every 2 weeks"
        else:
            appointment_frequency = "Every week"
    else:
        appointment_frequency = None
    
    # Get all chat messages
    all_messages = []
    message_indices = {}  # Track message indices for deletion
    for username, user_data in patients.items():
        if 'chat_messages' in user_data:
            for idx, msg in enumerate(user_data['chat_messages']):
                if msg.get('visible', True):  # Only show visible messages
                    msg_with_index = msg.copy()
                    msg_with_index['user_owner'] = username
                    msg_with_index['original_index'] = idx
                    all_messages.append(msg_with_index)
    all_messages.sort(key=lambda x: x.get('timestamp', ''))
    
    # Get new feature data
    weekly_tip = get_weekly_tips(patient.get('pregnancy_week', 8)) if patient.get('pregnancy_week') else None
    faq_list = get_faq()
    hospital_bag_checklist = get_hospital_bag_checklist()
    today = now_et().strftime('%Y-%m-%d')
    
    return render_template('dashboard.html', patient=patient, reminders=reminders, 
                         symptoms=symptoms, vaccine_info=vaccine_info, 
                         treatment_benefits=treatment_benefits, supplement_info=supplement_info,
                         exercise_videos=exercise_videos, appointment_frequency=appointment_frequency,
                         management_visuals=management_visuals, daily_quote=daily_quote,
                         additional_exercises=additional_exercises, exercise_importance=exercise_importance,
                         labwork_explanations=labwork_explanations, appointment_countdown=appointment_countdown,
                         all_messages=all_messages, current_user=session['username'],
                         hospital_portals=hospital_portals, appointment_status=appointment_status,
                         all_vaccines_caught_up=all_vaccines_caught_up, weekly_tip=weekly_tip,
                         faq_list=faq_list, hospital_bag_checklist=hospital_bag_checklist, today=today)
@app.route('/update_week', methods=['POST'])
def update_week():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    week = request.form.get('week')
    trimester = request.form.get('trimester')
    month = request.form.get('month')
    
    patients = load_patients()
    
    if week:
        patients[session['username']]['pregnancy_week'] = int(week)
        patients[session['username']]['week_set_date'] = now_et().strftime('%Y-%m-%d')
    elif trimester:
        converted_week = convert_to_weeks(trimester=trimester)
        if converted_week:
            patients[session['username']]['pregnancy_week'] = converted_week
            patients[session['username']]['trimester'] = trimester
            patients[session['username']]['week_set_date'] = now_et().strftime('%Y-%m-%d')
    elif month:
        converted_week = convert_to_weeks(month=month)
        if converted_week:
            patients[session['username']]['pregnancy_week'] = converted_week
            patients[session['username']]['month'] = month
            patients[session['username']]['week_set_date'] = now_et().strftime('%Y-%m-%d')
    
    save_patients(patients)
    return redirect('/dashboard#pregnancy-week')

@app.route('/update_email_settings', methods=['POST'])
def update_email_settings():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    patients = load_patients()
    patients[session['username']]['email'] = request.form.get('email')
    patients[session['username']]['reminder_time'] = request.form.get('reminder_time')
    save_patients(patients)
    
    return redirect('/dashboard#daily-log')

@app.route('/update_vaccines', methods=['POST'])
def update_vaccines():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    from datetime import datetime
    vaccines = request.form.getlist('vaccines')
    vaccine_date = request.form.get('vaccine_date', now_et().strftime('%Y-%m-%d'))
    
    patients = load_patients()
    
    # Initialize vaccine tracking with dates
    if 'vaccines_tracking' not in patients[session['username']]:
        patients[session['username']]['vaccines_tracking'] = {}
    
    # Update vaccines with date
    for vaccine in vaccines:
        if vaccine not in patients[session['username']]['vaccines_tracking']:
            patients[session['username']]['vaccines_tracking'][vaccine] = vaccine_date
    
    patients[session['username']]['vaccines_received'] = list(patients[session['username']]['vaccines_tracking'].keys())
    save_patients(patients)
    
    return redirect('/dashboard#checklist')

@app.route('/uncheck_vaccine', methods=['POST'])
def uncheck_vaccine():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    vaccine = request.form['vaccine']
    
    patients = load_patients()
    if 'vaccines_tracking' in patients[session['username']]:
        if vaccine in patients[session['username']]['vaccines_tracking']:
            del patients[session['username']]['vaccines_tracking'][vaccine]
    
    patients[session['username']]['vaccines_received'] = list(patients[session['username']].get('vaccines_tracking', {}).keys())
    save_patients(patients)
    
    return redirect('/dashboard#checklist')

@app.route('/update_tasks', methods=['POST'])
def update_tasks():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    from datetime import datetime
    tasks = request.form.getlist('tasks')
    task_date = request.form.get('task_date', now_et().strftime('%Y-%m-%d'))
    
    patients = load_patients()
    
    # Initialize task tracking with dates
    if 'tasks_tracking' not in patients[session['username']]:
        patients[session['username']]['tasks_tracking'] = {}
    
    # Update tasks with date
    for task in tasks:
        if task not in patients[session['username']]['tasks_tracking']:
            patients[session['username']]['tasks_tracking'][task] = task_date
    
    patients[session['username']]['completed_tasks'] = list(patients[session['username']]['tasks_tracking'].keys())
    save_patients(patients)
    
    return redirect('/dashboard#checklist')

@app.route('/uncheck_task', methods=['POST'])
def uncheck_task():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    task = request.form['task']
    
    patients = load_patients()
    if 'tasks_tracking' in patients[session['username']]:
        if task in patients[session['username']]['tasks_tracking']:
            del patients[session['username']]['tasks_tracking'][task]
    
    patients[session['username']]['completed_tasks'] = list(patients[session['username']].get('tasks_tracking', {}).keys())
    save_patients(patients)
    
    return redirect('/dashboard#checklist')

@app.route('/update_zipcode', methods=['POST'])
def update_zipcode():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    zipcode = request.form['zipcode']
    patients = load_patients()
    patients[session['username']]['zipcode'] = zipcode
    save_patients(patients)
    
    return redirect('/dashboard#exercise-programs')

@app.route('/add_daily_log', methods=['POST'])
def add_daily_log():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    bp = request.form['blood_pressure']
    glucose = request.form['glucose']
    
    warnings, classification = check_abnormal_values(bp, glucose)
    
    log_entry = {
        'date': request.form['date'],
        'blood_pressure': bp,
        'glucose': glucose,
        'weight': request.form.get('weight', ''),
        'warnings': warnings,
        'classification': classification
    }
    
    patients = load_patients()
    if 'daily_logs' not in patients[session['username']]:
        patients[session['username']]['daily_logs'] = []
    patients[session['username']]['daily_logs'].append(log_entry)
    save_patients(patients)
    
    return redirect('/dashboard#daily-log')

@app.route('/set_reminder', methods=['POST'])
def set_reminder():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    reminder_time = request.form['reminder_time']
    phone = request.form.get('phone', '')
    
    patients = load_patients()
    patients[session['username']]['reminder_time'] = reminder_time
    patients[session['username']]['reminder_phone'] = phone
    save_patients(patients)
    
    return redirect('/dashboard#daily-log')

@app.route('/delete_reminder', methods=['POST'])
def delete_reminder():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    patients = load_patients()
    patients[session['username']]['reminder_time'] = ''
    patients[session['username']]['reminder_phone'] = ''
    save_patients(patients)
    
    return redirect('/dashboard#daily-log')

@app.route('/set_appointment', methods=['POST'])
def set_appointment():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    appointment_date = request.form['appointment_date']
    appointment_time = request.form.get('appointment_time', '')
    patients = load_patients()
    patients[session['username']]['next_appointment'] = appointment_date
    patients[session['username']]['appointment_time'] = appointment_time
    save_patients(patients)
    
    return redirect('/dashboard#appointments')

@app.route('/sync_hospital_portal', methods=['POST'])
def sync_hospital_portal():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Placeholder for hospital portal integration
    # In production, this would connect to hospital API
    patients = load_patients()
    patients[session['username']]['hospital_portal_synced'] = True
    save_patients(patients)
    
    return redirect('/dashboard#hospital-portal')

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    from datetime import datetime
    import re
    message_text = request.form['message']
    is_clinician = request.form.get('is_clinician', 'false') == 'true'
    notify_emergency = request.form.get('notify_emergency', 'false') == 'true'
    
    patients = load_patients()
    
    # Get all usernames who have posted in chat
    chat_usernames = set()
    for username, user_data in patients.items():
        if user_data.get('chat_messages'):
            for msg in user_data['chat_messages']:
                if msg.get('visible', True):
                    chat_usernames.add(msg['username'])
    
    # Block phone numbers
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b'
    if re.search(phone_pattern, message_text, re.IGNORECASE):
        session['chat_error'] = 'Phone numbers are not allowed in community chat for privacy'
        return redirect('/dashboard#chat')
    
    # Check @mentions - only allow if user exists in chat
    mentions = re.findall(r'@(\w+)', message_text)
    for mention in mentions:
        if mention not in chat_usernames:
            session['chat_error'] = f'Cannot tag @{mention} - user not found in chat. Only tag users who have posted.'
            return redirect('/dashboard')
    
    # Block other social media and contact patterns
    blocked_patterns = [
        r'instagram\.com',
        r'facebook\.com',
        r'twitter\.com',
        r'snapchat',
        r'tiktok',
        r'whatsapp',
        r'\bDM me\b',
        r'\btext me\b',
        r'\bcall me\b',
        r'\bmy username\b',
        r'\busername is\b',
        r'\bmy name is\b',
        r'\bcall\s+\w+\b',
        r'\bcontact me\b',
        r'\beach out\b'
    ]
    
    for pattern in blocked_patterns:
        if re.search(pattern, message_text, re.IGNORECASE):
            session['chat_error'] = 'Contact info and social media are not allowed in community chat'
            return redirect('/dashboard')
    
    # Check for crisis keywords
    is_flagged = check_crisis_keywords(message_text)
    
    message = {
        'username': session['username'],
        'text': message_text,
        'timestamp': now_et().strftime('%Y-%m-%d %H:%M:%S'),
        'is_clinician': is_clinician,
        'flagged': is_flagged,
        'visible': not is_flagged,  # Hide flagged messages from community
        'can_delete': True  # Allow patient to delete even if flagged
    }
    
    patients = load_patients()
    if 'chat_messages' not in patients[session['username']]:
        patients[session['username']]['chat_messages'] = []
    patients[session['username']]['chat_messages'].append(message)
    
    # Create emergency alert for clinicians if flagged
    if is_flagged:
        # Alert to clinicians (can be deleted by patient)
        alert = {
            'username': 'SYSTEM',
            'text': f'🚨 EMERGENCY ALERT: Patient {session["username"]} may need immediate support. Please contact them urgently.',
            'timestamp': now_et().strftime('%Y-%m-%d %H:%M:%S'),
            'is_clinician': True,
            'flagged': False,
            'visible': True,
            'is_alert': True,
            'can_delete': True,  # Patient can delete this
            'owner': session['username']  # Track who owns this alert
        }
        patients[session['username']]['chat_messages'].append(alert)
        
        # Confirmation message to patient
        confirmation = {
            'username': 'SYSTEM',
            'text': '✓ Your care team has been alerted and will get back to you shortly. You are not alone.',
            'timestamp': now_et().strftime('%Y-%m-%d %H:%M:%S'),
            'is_clinician': True,
            'flagged': False,
            'visible': True,
            'is_confirmation': True,
            'can_delete': False
        }
        patients[session['username']]['chat_messages'].append(confirmation)
        
        # Send alerts to emergency contacts only if patient chose to notify them
        if notify_emergency and 'emergency_contacts' in patients[session['username']]:
            emergency_contacts = patients[session['username']]['emergency_contacts']
            if emergency_contacts:
                alerts = send_emergency_alert(session['username'], emergency_contacts)
                # Store alert record
                if 'emergency_alerts' not in patients[session['username']]:
                    patients[session['username']]['emergency_alerts'] = []
                patients[session['username']]['emergency_alerts'].extend(alerts)
    
    save_patients(patients)
    return redirect('/dashboard')

@app.route('/delete_message', methods=['POST'])
def delete_message():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    from datetime import datetime
    message_index = int(request.form['message_index'])
    message_owner = request.form['message_owner']
    is_clinician = request.form.get('is_clinician', 'false') == 'true'
    
    patients = load_patients()
    
    # Get the correct user's messages
    if message_owner in patients:
        user_messages = patients[message_owner].get('chat_messages', [])
        
        if message_index < len(user_messages):
            message = user_messages[message_index]
            
            # Only allow users to delete their OWN messages
            if message['username'] != session['username']:
                return jsonify({'error': 'Cannot delete other users messages'}), 403
            
            # Check if this is a clinician alert being deleted
            is_alert_deleted = message.get('is_alert', False) and message.get('owner') == session['username']
            
            # Users can only delete their own messages
            if message['username'] == session['username'] and message.get('can_delete', True):
                user_messages.pop(message_index)
                
                # If clinician alert was deleted, send follow-up to clinician
                if is_alert_deleted:
                    followup = {
                        'username': 'SYSTEM',
                        'text': f'📋 Follow-up: Patient {session["username"]} deleted their crisis alert. Please still reach out to check on their wellbeing.',
                        'timestamp': now_et().strftime('%Y-%m-%d %H:%M:%S'),
                        'is_clinician': True,
                        'flagged': False,
                        'visible': True,
                        'is_followup': True,
                        'can_delete': False
                    }
                    user_messages.append(followup)
                
                patients[message_owner]['chat_messages'] = user_messages
                save_patients(patients)
    
    return redirect('/dashboard#chat')

@app.route('/add_emergency_contact', methods=['POST'])
def add_emergency_contact():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    patients = load_patients()
    if 'emergency_contacts' not in patients[session['username']]:
        patients[session['username']]['emergency_contacts'] = []
    
    # Limit to 2 emergency contacts
    if len(patients[session['username']]['emergency_contacts']) >= 2:
        return redirect('/dashboard#emergency-contacts')
    
    contact = {
        'name': request.form['contact_name'],
        'phone': request.form['contact_phone'],
        'relationship': request.form['relationship'],
        'auto_notify': request.form.get('auto_notify') == 'on'
    }
    
    patients[session['username']]['emergency_contacts'].append(contact)
    save_patients(patients)
    
    return redirect('/dashboard')

@app.route('/update_emergency_contact', methods=['POST'])
def update_emergency_contact():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    contact_index = int(request.form['contact_index'])
    
    patients = load_patients()
    if 'emergency_contacts' in patients[session['username']]:
        if contact_index < len(patients[session['username']]['emergency_contacts']):
            patients[session['username']]['emergency_contacts'][contact_index] = {
                'name': request.form['contact_name'],
                'phone': request.form['contact_phone'],
                'relationship': request.form['relationship'],
                'auto_notify': request.form.get('auto_notify') == 'on'
            }
            save_patients(patients)
    
    return redirect('/dashboard#emergency-contacts')

@app.route('/delete_emergency_contact', methods=['POST'])
def delete_emergency_contact():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    contact_index = int(request.form['contact_index'])
    
    patients = load_patients()
    if 'emergency_contacts' in patients[session['username']]:
        patients[session['username']]['emergency_contacts'].pop(contact_index)
    save_patients(patients)
    
    return redirect('/dashboard#emergency-contacts')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')

@app.route('/reset_data', methods=['POST'])
def reset_data():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    patients = load_patients()
    if session['username'] in patients:
        # Keep only username and password
        password = patients[session['username']]['password']
        patients[session['username']] = {
            'password': password,
            'pregnancy_week': None,
            'vaccines_received': [],
            'completed_tasks': [],
            'zipcode': '',
            'daily_logs': [],
            'reminder_time': '',
            'next_appointment': '',
            'trimester': '',
            'month': '',
            'hospital_portal_synced': False,
            'chat_messages': [],
            'emergency_contacts': [],
            'email': '',
            'medications': [],
            'weight_logs': [],
            'kick_counts': [],
            'contractions': [],
            'birth_plan': {},
            'hospital_bag': [],
            'appointments_history': []
        }
        save_patients(patients)
    
    return redirect('/dashboard#about')

@app.route('/add_medication', methods=['POST'])
def add_medication():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    patients = load_patients()
    if 'medications' not in patients[session['username']]:
        patients[session['username']]['medications'] = []
    
    med = {
        'name': request.form['med_name'],
        'dosage': request.form['dosage'],
        'frequency': request.form['frequency'],
        'time': request.form.get('med_time', '')
    }
    patients[session['username']]['medications'].append(med)
    save_patients(patients)
    return redirect('/dashboard#medications')

@app.route('/delete_medication', methods=['POST'])
def delete_medication():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    med_index = int(request.form['med_index'])
    patients = load_patients()
    if 'medications' in patients[session['username']]:
        patients[session['username']]['medications'].pop(med_index)
    save_patients(patients)
    return redirect('/dashboard#medications')

@app.route('/log_weight', methods=['POST'])
def log_weight():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    patients = load_patients()
    if 'weight_logs' not in patients[session['username']]:
        patients[session['username']]['weight_logs'] = []
    
    log = {
        'weight': request.form['weight'],
        'date': request.form.get('weight_date', now_et().strftime('%Y-%m-%d'))
    }
    patients[session['username']]['weight_logs'].append(log)
    save_patients(patients)
    return redirect('/dashboard#weight')

@app.route('/log_kicks', methods=['POST'])
def log_kicks():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    patients = load_patients()
    if 'kick_counts' not in patients[session['username']]:
        patients[session['username']]['kick_counts'] = []
    
    log = {
        'count': request.form['kick_count'],
        'duration': request.form['duration'],
        'timestamp': now_et().strftime('%Y-%m-%d %H:%M:%S')
    }
    patients[session['username']]['kick_counts'].append(log)
    save_patients(patients)
    return redirect('/dashboard#kicks')

@app.route('/log_contraction', methods=['POST'])
def log_contraction():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    patients = load_patients()
    if 'contractions' not in patients[session['username']]:
        patients[session['username']]['contractions'] = []
    
    log = {
        'duration': request.form['contraction_duration'],
        'intensity': request.form['intensity'],
        'timestamp': now_et().strftime('%Y-%m-%d %H:%M:%S')
    }
    patients[session['username']]['contractions'].append(log)
    save_patients(patients)
    return redirect('/dashboard#contractions')

@app.route('/save_birth_plan', methods=['POST'])
def save_birth_plan():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    patients = load_patients()
    patients[session['username']]['birth_plan'] = {
        'delivery_preference': request.form.get('delivery_preference', ''),
        'pain_management': request.form.get('pain_management', ''),
        'support_person': request.form.get('support_person', ''),
        'special_requests': request.form.get('special_requests', '')
    }
    save_patients(patients)
    return redirect('/dashboard#birth-plan')

@app.route('/toggle_hospital_bag', methods=['POST'])
def toggle_hospital_bag():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    item = request.form['item']
    patients = load_patients()
    if 'hospital_bag' not in patients[session['username']]:
        patients[session['username']]['hospital_bag'] = []
    
    if item in patients[session['username']]['hospital_bag']:
        patients[session['username']]['hospital_bag'].remove(item)
    else:
        patients[session['username']]['hospital_bag'].append(item)
    
    save_patients(patients)
    
    return redirect('/dashboard#hospital-bag')

@app.route('/admin/users')
def admin_users():
    if 'username' not in session:
        return redirect('/')
    
    # You can add admin user check here if needed
    # For now, any logged-in user can access (you may want to restrict this)
    
    patients = load_patients()
    user_list = []
    
    for username, data in patients.items():
        user_info = {
            'username': username,
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'gmail': data.get('gmail', ''),
            'pregnancy_week': data.get('pregnancy_week', 'Not set'),
            'due_date': data.get('due_date', 'Not set'),
            'registration_date': data.get('registration_date', 'Unknown'),
            'last_login': data.get('last_login', 'Never')
        }
        user_list.append(user_info)
    
    return render_template('admin_users.html', users=user_list, total_users=len(user_list))

if __name__ == '__main__':
    # Start background scheduler for email reminders
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=send_daily_reminders, trigger="interval", minutes=1)  # Check every minute
    scheduler.start()
    
    try:
        app.run(debug=False, host='0.0.0.0', port=5000)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
