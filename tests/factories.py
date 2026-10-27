"""Small helpers so each test reads as the scenario it is testing."""

from datetime import date

from django.contrib.auth import get_user_model

from apps.doctors.models import Doctor
from apps.patients.models import Patient

User = get_user_model()

DEFAULT_PASSWORD = "StrongPass!234"


def make_user(email="owner@example.com", name="Owner User", password=DEFAULT_PASSWORD):
    return User.objects.create_user(email=email, name=name, password=password)


def make_patient(created_by, **overrides):
    data = {
        "full_name": "Asha Mehta",
        "date_of_birth": date(1990, 5, 17),
        "gender": Patient.Gender.FEMALE,
        "blood_group": Patient.BloodGroup.O_POS,
        "phone": "+919876543210",
        "email": "asha@example.com",
        "address": "12 Linking Road, Mumbai",
        "medical_history": "Mild asthma.",
    }
    data.update(overrides)
    return Patient.objects.create(created_by=created_by, **data)


def make_doctor(created_by, **overrides):
    data = {
        "full_name": "Rohan Kapoor",
        "specialization": Doctor.Specialization.CARDIOLOGY,
        "license_number": "MCI-10045",
        "email": "rohan.kapoor@example.com",
        "phone": "+919812345678",
        "years_of_experience": 12,
        "consultation_fee": "850.00",
    }
    data.update(overrides)
    return Doctor.objects.create(created_by=created_by, **data)
