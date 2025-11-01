from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Load saved credentials from token.json
creds = Credentials.from_authorized_user_file("token.json")

# Connect to Gmail API
service = build('gmail', 'v1', credentials=creds)

# Get unread emails
results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
messages = results.get('messages', [])

if not messages:
    print("✅ No unread emails found.")
else:
    print(f"📨 You have {len(messages)} unread emails.\n")
    for msg in messages[:5]:  # show up to 5 messages
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        snippet = msg_data.get('snippet')
        print(f"- {snippet}\n")
