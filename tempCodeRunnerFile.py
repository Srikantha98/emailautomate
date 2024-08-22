from flask import Flask, redirect, request, url_for, jsonify, render_template
from flask_session import Session
import email_handler
import openai
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Set your OpenAI API key here
openai.api_key = 'sk-pRsE5okuef2ZPAxXcdKX0Va5awamYw-34rgew7fp7YT3BlbkFJrKndSrh9R3dQVuUw8K-EhJXJK_2129BrXX5JJLNBQA'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/authorize')
def authorize():
    auth_url = email_handler.get_auth_url()
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    email_handler.handle_oauth_callback(request.url)
    return redirect(url_for('check_and_reply'))

@app.route('/check_and_reply')
def check_and_reply():
    # Authenticate with Gmail
    service = email_handler.authenticate_gmail()

    if service:
        messages = email_handler.fetch_unread_emails(service)
        for message in messages:
            email_data = email_handler.parse_email(service, message['id'])
            if email_data:
                response_text = generate_response(email_data['body'])
                reply_message = email_handler.create_message(
                    to=email_data['from'],
                    subject=f"Re: {email_data['subject']}",
                    message_text=response_text
                )
                email_handler.send_message(service, 'me', reply_message)
                categorize_email(service, message['id'], email_data['body'])

    return jsonify({'status': 'done'})

def generate_response(email_body):
    prompt = f"Respond to the following email:\n\n{email_body}\n\nResponse:"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    return response.choices[0].text.strip()

def categorize_email(service, message_id, email_body):
    label = determine_label(email_body)
    email_handler.add_label(service, message_id, label)

def determine_label(email_body):
    prompt = f"Categorize the following email into one of the labels: Interested, Not Interested, More Information:\n\n{email_body}\n\nLabel:"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=10
    )
    return response.choices[0].text.strip()

if __name__ == '__main__':
    app.run(debug=True)
