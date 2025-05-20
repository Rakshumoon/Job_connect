import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit
from transformers import BertTokenizer, BertModel
from sklearn.metrics.pairwise import cosine_similarity

rooms = {'job_recruiter': [], 'job_seeker': []}
# Initialize BERT tokenizer and model
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
bert_model = BertModel.from_pretrained('bert-base-uncased')

def get_bert_embedding(text):
    """Generate BERT embedding for a given text."""
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
    outputs = bert_model(**inputs)
    # Use the [CLS] token embedding as a representative of the sentence
    cls_embedding = outputs.last_hidden_state[:, 0, :].detach().numpy()
    return cls_embedding


print("Templates:", os.listdir('templates'))

# Flask setup
app = Flask(__name__, template_folder=os.path.join(os.getcwd(), 'templates'))
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)


# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Temporary storage for demonstration
job_seekers = []  # To store job seekers' data
job_recruiters = []  # To store job recruiters' data

# Static data for companies
COMPANY_DATA = {
    "Google": {
        "description": "A leading tech company specializing in AI and cloud computing.",
        "vacancies": [
            {"title": "Software Engineer", "location": "Mountain View, CA"},
            {"title": "Data Scientist", "location": "New York, NY"}
        ]
    },
    "Microsoft": {
        "description": "A global leader in software, hardware, and cloud solutions.",
        "vacancies": [
            {"title": "Cloud Engineer", "location": "Seattle, WA"},
            {"title": "Product Manager", "location": "San Francisco, CA"}
        ]
    },
    "Infosys": {
        "description": "A multinational IT services and consulting company.",
        "vacancies": [
            {"title": "Business Analyst", "location": "Bangalore, India"},
            {"title": "Full Stack Developer", "location": "Pune, India"}
        ]
    }
}


# Utility function to check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Home page route
@app.route('/home')
def home():
    if 'user' in session:
        email = session['user']  # Retrieve the user's email from the session
        matches = match_job_seekers_and_recruiters()  # Replace with your matching logic
        return render_template('home.html', email=email, matches=matches)
    else:
        return redirect(url_for('login'))  # Redirect to login if user is not logged in

# Job Seeker Form
# Job Seeker Form Route
@app.route('/job_seeker', methods=['GET', 'POST'])
def job_seeker():
    if request.method == 'POST':
        # Capture form data for Job Seeker
        seeker_data = {
            'name': request.form.get('name'),
            'expected_salary': request.form.get('expected_salary'),
            'qualifications': request.form.get('qualifications'),
            'experience': request.form.get('experience'),
            'job_position': request.form.get('job_position'),
            'extra_qualifications': request.form.get('extra_qualifications'),
            'interested_companies': request.form.get('interested_companies'),
        }
        
        # Append the captured data to the job seekers list
        job_seekers.append(seeker_data)

        # Redirect to home page after submission
        return redirect(url_for('home'))

    return render_template('job_seeker.html')

# Job Recruiter Form Route
# Job Recruiter Form Route
@app.route('/job_recruiter', methods=['GET', 'POST'])
def job_recruiter():
    if request.method == 'POST':
        # Capture form data for Job Recruiter
        recruiter_data = {
            'name': request.form.get('name'),
            'company_name': request.form.get('company_name'),
            'position': request.form.get('position'),
            'required_position': request.form.get('required_position'),
            'min_salary': request.form.get('min_salary'),
            'experience_expected': request.form.get('experience_expected'),
            'qualifications': request.form.get('qualifications'),
            'extra_qualifications': request.form.get('extra_qualifications'),
        }

        # Append the captured data to the job recruiters list
        job_recruiters.append(recruiter_data)

        # Redirect to home page after submission
        return redirect(url_for('home'))

    return render_template('job_recruiter.html')

@socketio.on('connect')
def handle_connect():
    pass  # Placeholder for handling user connection

# Match Results Page
def match_job_seekers_and_recruiters():
    matches = []
    for seeker in job_seekers:
        seeker_text = f"{seeker['job_position']} {seeker['qualifications']} {seeker['experience']}"
        seeker_embedding = get_bert_embedding(seeker_text)

        for recruiter in job_recruiters:
            recruiter_text = f"{recruiter['required_position']} {recruiter['qualifications']} {recruiter['experience_expected']}"
            recruiter_embedding = get_bert_embedding(recruiter_text)

            # Compute cosine similarity
            similarity = cosine_similarity(seeker_embedding, recruiter_embedding)[0][0]
            if similarity > 0.8:  # Matching threshold
                matches.append({'seeker': seeker, 'recruiter': recruiter, 'similarity': similarity})
    return matches



# Resume Builder Form
@app.route('/resume_builder', methods=['GET', 'POST'])
def resume_builder():
    if request.method == 'POST':
        try:
            # Extract details from form
            details = {
                'name': request.form['name'],
                'college':request.form['college'],
                'cgpa':request.form['cgpa'],
                'school':request.form['school'],
                'percentage':request.form['percentage'],
                'email': request.form['email'],
                'skills': request.form['skills'].splitlines(),
                'experience': request.form['experience'],
                'education': request.form['education'],
                'professional_summary': request.form['professional_summary'],
                'desired_companies': request.form['desired_companies'].splitlines(),
                'projects': request.form['projects'].splitlines(),
                'certifications': request.form['certifications'].splitlines(),
                'languages': request.form['languages'].splitlines(),
                'awards': request.form['awards'].splitlines(),
                'volunteer_experience': request.form['volunteer_experience'],
                'interests': request.form['interests'].splitlines(),
            }
            selected_template = request.form['template']

            profile_image = request.files.get('profile_image')
            image_path = ''
            if profile_image and allowed_file(profile_image.filename):
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(profile_image.filename))
                profile_image.save(image_path)

            details['profile_image'] = image_path

            # Validate template selection
            if selected_template not in ['template1', 'template2', 'template3', 'template4', 'template5']:
                raise ValueError("Invalid template selected")

            # Generate recommendations
            recommendations = [
                ("Software Engineer", "Develop software systems", 0.95),
                ("Data Analyst", "Analyze datasets for insights", 0.87),
                ("Project Manager", "Oversee project execution", 0.78),
            ]

            # Render the selected template with modal recommendations
            return render_template(
                f"{selected_template}.html",
                details=details,
                recommendations=recommendations,
                show_modal=True  # Indicate to show the modal
            )

        except Exception as e:
            return f"Error: {str(e)}", 400  # Return a more meaningful error message

    # Initial GET request
    return render_template('resume_builder.html', recommendations=[], details=None, selected_template=None)

@app.route('/resume_decision', methods=['GET'])
def resume_decision():
    # Retrieve details and recommendations from the session
    details = session.get('details')
    recommendations = session.get('recommendations')

    return render_template('resume_decision.html', details=details, recommendations=recommendations)


@app.route('/save_resume', methods=['POST'])
def save_resume():
    # Capture form data
    profile_image = request.files.get('profile_image')
    name = request.form.get('name')
    email = request.form.get('email')
    skills = request.form.get('skills')
    experience = request.form.get('experience')
    education = request.form.get('education')
    desired_companies = request.form.get('desired_companies')
    projects = request.form.get('projects')
    certifications = request.form.get('certifications')
    languages = request.form.get('languages')
    awards = request.form.get('awards')
    volunteer_experience = request.form.get('volunteer_experience')
    interests = request.form.get('interests')

    # Define the upload folder and image path
    image_path = ''
    if profile_image:
        # Define the directory for storing images
        upload_folder = os.path.join('static', 'profile_image')

        # Ensure the directory exists
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)  # Create the directory if it doesn't exist

        # Define the path to save the file
        image_path = os.path.join(upload_folder, profile_image.filename)
        profile_image.save(image_path)  # Save the uploaded image

    # Store data in session
    session['resume_data'] = {
        'profile_image': image_path,
        'name': name,
        'email': email,
        'skills': skills,
        'experience': experience,
        'education': education,
        'desired_companies': desired_companies,
        'projects': projects,
        'certifications': certifications,
        'languages': languages,
        'awards': awards,
        'volunteer_experience': volunteer_experience,
        'interests': interests
    }

    # Render the confirmation page
    return redirect(url_for('select_template'))


@app.route('/profile_creation', methods=['GET', 'POST'])
def update_profile():
    if request.method == 'POST':
        # Handle form data
        job_sought = request.form.get('job_sought')
        work_experience = request.form.get('work_experience')
        qualifications = request.form.get('qualifications')
        gender = request.form.get('gender')

        # Check if a file is part of the form
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and allowed_file(file.filename):
                user_id = request.form['user_id']  # Assuming you have a unique user ID
                filename = f"{user_id}_{file.filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                # Store the image URL or file path to be displayed
                image_url = url_for('uploaded_file', filename=filename)
            else:
                image_url = None
        else:
            image_url = None

        # Optionally, store the profile data in the session or database here

        # Return the profile creation page with the updated data
        return render_template('profile_creation.html', job_sought=job_sought, 
                               work_experience=work_experience, qualifications=qualifications,
                               gender=gender, image_url=image_url)

    return render_template('profile_creation.html', image_url=None)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return redirect(url_for('static', filename=f'uploads/{filename}'))


# Socket.IO chat functionality
@socketio.on('send_message')
def handle_send_message(message):
    # Broadcast the message to all connected clients
    emit('receive_message', message, broadcast=True)



@app.route('/select_template')
def select_template():
    return render_template('select_template.html')


@app.route('/generate_resume', methods=['GET'])
def generate_resume():
    details = session.get('details')
    return render_template('generate_resume.html', details=details)


# Static Company Pages
@app.route('/company/<company_name>')
def company_page(company_name):
    company = COMPANY_DATA.get(company_name)
    if not company:
        return "Company not found", 404
    return render_template('company.html', company_name=company_name, company=company)



# About Us Page Route
@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

# Contact Us Page Route
@app.route('/contact_us', methods=['GET', 'POST'])
def contact_us():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        # Debugging Output (optional)
        print(f"Name: {name}, Email: {email}, Message: {message}")

        # Response after form submission
        return "Thank you for contacting us! We'll get back to you shortly."
    return render_template('contact_us.html')
print("Route '/about_us' registered")
print("Route '/contact_us' registered")



@app.route('/company/google')
def google():
    return render_template('google.html')

@app.route('/company/microsoft')
def microsoft():
    return render_template('microsoft.html')

@app.route('/company/infosys')
def infosys():
    return render_template('infosys.html')

@app.route('/company/amazon')
def amazon():
    return render_template('amazon.html')

@app.route('/company/tcs')
def tcs():
    return render_template('tcs.html')


@app.route('/')
def welcome():
    return render_template('welcome.html')

# Sign-Up Page
@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Mocked user storage (replace with database in production)
        session['user_data'] = {
            'email': email,
            'password': password
        }
        return redirect(url_for('login'))

    return render_template('sign_up.html')

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get email from the form and store it in the session
        email = request.form.get('email')
        session['user'] = email  # Save email in the session for identifying the user
        return redirect(url_for('home'))  # Redirect directly to the home page

    return render_template('login.html')



# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('welcome'))

@app.route('/favicon.ico')
def favicon():
    return '', 204  # Return an empty response


if __name__ == '_main_':
     socketio.run(app, host='127.0.0.1', port=5000)