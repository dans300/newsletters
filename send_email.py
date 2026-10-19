import os
import glob
import base64
import requests

print("--- STARTING EMAIL PROCESS (RESEND API) ---")

# 1. Grab API key from GitHub Actions environment

api_key = os.getenv("SEND_KEY")


# WARNING: On Resend's free tier, the "to" email MUST be the exact 
# email address you used to sign up for your Resend account.
receiver_email = "groupsomfy@gmail.com"
#

if not api_key:
    print("API_KEY not found. Ensure GitHub Secrets are set.")
    exit(1)

# 2. Find the PDF inside the output/ folder
pdf_files = glob.glob('output/*.pdf')

if not pdf_files:
    print("No PDF found in the output/ folder to attach.")
    exit(1)

pdf_file = pdf_files[0] 
attachment_name = os.path.basename(pdf_file)
print(f"Attaching {attachment_name}...")

# 3. Read and encode the PDF for the API
with open(pdf_file, 'rb') as f:
    pdf_base64 = base64.b64encode(f.read()).decode('utf-8')

# 4. Build the API request
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "from": "Acme <onboarding@resend.dev>", # Resend's default testing address
    "to": [receiver_email],
    "subject": "Your Generated Newsletter",
    "html": "<p>This week on the Competition news  .</p><p>Feedback is much appreciated! Best regards.  -Daniel</p>",
    "attachments": [
        {
            "filename": attachment_name,
            "content": pdf_base64
        }
    ]
}

# 5. Send it
try:
    print("Sending via Resend API...")
    response = requests.post("https://api.resend.com/emails", headers=headers, json=payload)
    
    if response.status_code == 200:
        print("Email sent successfully!")
    else:
        print(f"Failed to send email. Status code: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"An error occurred: {e}")