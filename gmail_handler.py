import os
import base64
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.modify']

def get_flow():
    return InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)

def authenticate_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = get_flow()
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        print(f'An error occurred: {e}')
        return None

def get_auth_url():
    flow = get_flow()
    auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    return auth_url

def handle_oauth_callback(url):
    flow = get_flow()
    flow.fetch_token(authorization_response=url)
    creds = flow.credentials
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

def fetch_unread_emails(service):
    try:
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
        messages = results.get('messages', [])
        return messages
    except Exception as e:
        print(f'An error occurred: {e}')
        return []

def parse_email(service, msg_id):
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = message['payload']
        headers = payload.get("headers")
        parts = payload.get("parts")
        email_data = {}

        for header in headers:
            if header.get("name") == 'From':
                email_data['from'] = header.get("value")
            if header.get("name") == "Subject":
                email_data['subject'] = header.get("value")

        if parts:
            body = ""
            for part in parts:
                if part.get("mimeType") == "text/plain":
                    body += part.get("body").get("data")
            email_data['body'] = base64.urlsafe_b64decode(body.encode('ASCII')).decode('utf-8')

        return email_data
    except Exception as e:
        print(f'An error occurred: {e}')
        return None

def create_message(to, subject, message_text):
    message = {
        'raw': base64.urlsafe_b64encode(f'To: {to}\r\nSubject: {subject}\r\n\r\n{message_text}'.encode('utf-8')).decode('utf-8')
    }
    return message

def send_message(service, user_id, message):
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        print(f"Message sent: {message}")
    except Exception as e:
        print(f'An error occurred: {e}')

def add_label(service, message_id, label_name):
    try:
        # Create or get label
        labels = service.users().labels().list(userId='me').execute().get('labels', [])
        label_id = None
        for label in labels:
            if label['name'] == label_name:
                label_id = label['id']
                break
        if not label_id:
            label = service.users().labels().create(userId='me', body={'name': label_name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}).execute()
            label_id = label['id']
        
        # Add label to message
        service.users().messages().modify(userId='me', id=message_id, body={'addLabelIds': [label_id]}).execute()
    except Exception as e:
        print(f'An error occurred: {e}')
