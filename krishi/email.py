# views.py
import random
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.mail import EmailMultiAlternatives
from .models import EmailOTP

class SendOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')

        otp = str(random.randint(100000, 999999))

        # Save OTP
        EmailOTP.objects.create(email=email, otp=otp)

        # Email content
        subject = "Verify your email"
        from_email = "nerdswayam@gmail.com"

        text = f"Your OTP is {otp}. Valid for 5 minutes. (Please check your spam folder if you do not see this email)"

        html = f"""
        <h2>Email Verification</h2>
        <p>Your OTP is:</p>
        <h1 style="color:#0f0f0f;"><b>{otp}</b></h1>
        <p>This OTP expires in 5 minutes.</p>
        <p><small>(Please check your spam folder if you do not see this email)</small></p>
        <br>
        <p>Thank you!</p>
        <p><b>Team KrishiScan!</B></p>
        """

        msg = EmailMultiAlternatives(subject, text, from_email, [email])
        msg.attach_alternative(html, "text/html")
        msg.send()

        return Response({"message": "OTP sent"})

class VerifyOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        record = EmailOTP.objects.filter(email=email).last()

        if record and record.otp == otp and record.is_valid():
            return Response({"message": "Verified"})
        
        return Response({"error": "Invalid or expired OTP"}, status=400)