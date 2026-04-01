import random
from twilio.rest import Client

def generate_otp():
    return str(random.randint(100000, 999999))

# Twilio credentials
account_sid = 'YOUR_ACCOUNT_SID'
auth_token = 'YOUR_AUTH_TOKEN'

client = Client(account_sid, auth_token)

def send_otp(phone_number, otp):
    message = client.messages.create(
        body=f"Your OTP is: {otp}",
        from_='+1234567890',  # Twilio phone number
        to=phone_number
    )
    return message.sid