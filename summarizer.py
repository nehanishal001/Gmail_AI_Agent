from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from openai import OpenAI
from dotenv import load_dotenv
import os
import base64
import json
import time

# Load .env file
load_dotenv()

# 🟢 Groq-compatible OpenAI client setup
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),          # uses Groq key from .env
    base_url="https://api.groq.com/openai/v1"   # Groq's OpenAI-compatible endpoint
)


def extract_text(msg):
    """Extract plain text body from the Gmail message"""
    payload = msg['payload']
    parts = payload.get('parts', [])
    data = ""
    if parts:
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                data = part['body'].get('data')
                break
    else:
        data = payload['body'].get('data')
    if data:
        return base64.urlsafe_b64decode(data).decode('utf-8')
    return ""


def summarize_emails():
    creds = Credentials.from_authorized_user_file("token.json")
    service = build('gmail', 'v1', credentials=creds)

    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
    messages = results.get('messages', [])

    if not messages:
        print("✅ No unread emails to summarize.")
        return

    # 🟢 Batch settings
    batch_size = 5
    email_batches = [messages[i:i + batch_size] for i in range(0, len(messages), batch_size)]

    for batch_num, batch in enumerate(email_batches, start=1):
        print(f"\n📦 Processing batch {batch_num} ({len(batch)} emails)...")

        email_texts = []
        for idx, msg in enumerate(batch, start=1):
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
            body = extract_text(msg_data)

            if len(body) > 3000:  # trim long emails
                body = body[:3000] + "...[truncated]"

            email_texts.append(f"Email {idx}:\nSubject: {subject}\nFrom: {sender}\nBody:\n{body}\n---")

        # 🧠 One combined batch prompt for summarization + classification
        batch_prompt = f"""
        You are an intelligent email assistant.

        For each email below:
        1️⃣ Summarize it in 2 lines.
        2️⃣ Categorize it as one of: Job, Promotion, or Important.
        3️⃣ Return the output strictly as valid JSON in this format:
        [
          {{"email": 1, "summary": "text here", "category": "Job"}},
          ...
        ]

        Emails:
        {chr(10).join(email_texts)}
        """

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": batch_prompt}],
                max_tokens=1200
            )
            ai_output = response.choices[0].message.content

            # 🟢 Parse the JSON output safely
            try:
                results = json.loads(ai_output)
            except json.JSONDecodeError:
                print("⚠️ Model returned invalid JSON, showing raw output instead:")
                print(ai_output)
                continue

            # 🧾 Display results
            print("\n📨 Batch Results:")
            for item in results:
                print(f"\n📧 Email {item.get('email', '?')}")
                print(f"Summary: {item.get('summary', '')}")
                print(f"Category: {item.get('category', '')}")

        except Exception as e:
            print(f"⚠️ Error processing batch: {e}")

        # 💤 Sleep to prevent 429 rate-limit
        time.sleep(2)


if __name__ == "__main__":
    summarize_emails()
