"""Populate the database with a small, realistic demo dataset.

Intended for local development and for demonstrating the API; it is
idempotent, so running it twice will not create duplicates.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.workspace import grant_workspace_access
from apps.doctors.models import Doctor
from apps.mappings.models import PatientDoctorMapping
from apps.patients.models import Patient

User = get_user_model()

DEMO_EMAIL = "demo@example.com"

DOCTORS = [
    ("Rohan Kapoor", Doctor.Specialization.CARDIOLOGY, "MCI-10045",
     "rohan.kapoor@example.com", "+919812345678", 12, "850.00"),
    ("Meera Iyer", Doctor.Specialization.NEUROLOGY, "MCI-20099",
     "meera.iyer@example.com", "+919823456789", 8, "1200.00"),
    ("Sanjay Nair", Doctor.Specialization.PAEDIATRICS, "MCI-30156",
     "sanjay.nair@example.com", "+919834567890", 15, "600.00"),
    ("Priya Desai", Doctor.Specialization.DERMATOLOGY, "MCI-40211",
     "priya.desai@example.com", "+919845678901", 6, "700.00"),
    ("Arjun Menon", Doctor.Specialization.ORTHOPAEDICS, "MCI-50388",
     "arjun.menon@example.com", "+919856789012", 20, "950.00"),
]

PATIENTS = [
    ("Asha Mehta", date(1990, 5, 17), Patient.Gender.FEMALE,
     Patient.BloodGroup.O_POS, "+919876543210", "asha.mehta@example.com",
     "12 Linking Road, Mumbai", "Mild asthma, managed with an inhaler."),
    ("Bharat Singh", date(1978, 11, 2), Patient.Gender.MALE,
     Patient.BloodGroup.B_POS, "+919876543211", "bharat.singh@example.com",
     "44 MG Road, Bengaluru", "Type 2 diabetes diagnosed in 2015."),
    ("Chetna Rao", date(2015, 3, 9), Patient.Gender.FEMALE,
     Patient.BloodGroup.A_NEG, "+919876543212", "chetna.rao@example.com",
     "8 Park Street, Kolkata", "Seasonal allergies."),
    ("Dev Sharma", date(1962, 7, 24), Patient.Gender.MALE,
     Patient.BloodGroup.AB_POS, "+919876543213", "dev.sharma@example.com",
     "21 Civil Lines, Delhi", "Hypertension; post-operative knee review."),
]

# (patient index, doctor index, is_primary, notes)
ASSIGNMENTS = [
    (0, 0, True, "Primary physician; annual cardiac review."),
    (0, 3, False, "Referred for a recurring skin rash."),
    (1, 0, True, "Primary physician; blood pressure monitoring."),
    (2, 2, True, "Primary paediatrician."),
    (3, 4, True, "Primary physician; knee replacement follow-up."),
    (3, 1, False, "Referred for suspected nerve impingement."),
]


class Command(BaseCommand):
    help = "Create a demo user with sample patients, doctors and assignments."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default=DEMO_EMAIL,
            help=f"Owner of the demo records (default: {DEMO_EMAIL}).",
        )
        parser.add_argument(
            "--password",
            help=(
                "Give the demo account this password plus admin access to "
                "patients, doctors and mappings, so a visitor can sign in "
                "and try the app. Omitted, the account keeps an unusable "
                "password and is only something to own the records."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        email = options["email"].lower()
        password = options["password"]
        owner, created = User.objects.get_or_create(
            email=email, defaults={"name": "Demo User"}
        )
        if password:
            owner.set_password(password)
            owner.save()
            # No delete: this account is shared, so one visitor must not
            # be able to empty the demo for the next.
            grant_workspace_access(owner, allow_delete=False)
            self.stdout.write(
                f"{'Created' if created else 'Updated'} demo user {email} "
                "with a password and admin access to the demo tables"
            )
        elif created:
            # Unusable password: this account is for viewing data in the
            # admin, not for logging in as.
            owner.set_unusable_password()
            owner.save()
            self.stdout.write(f"Created demo user {email}")
        else:
            self.stdout.write(f"Reusing existing user {email}")

        doctors = []
        for name, spec, licence, mail, phone, years, fee in DOCTORS:
            doctor, _ = Doctor.objects.get_or_create(
                license_number=licence,
                defaults={
                    "created_by": owner,
                    "full_name": name,
                    "specialization": spec,
                    "email": mail,
                    "phone": phone,
                    "years_of_experience": years,
                    "consultation_fee": Decimal(fee),
                },
            )
            doctors.append(doctor)

        patients = []
        for name, dob, gender, blood, phone, mail, address, history in PATIENTS:
            patient, _ = Patient.objects.get_or_create(
                created_by=owner,
                phone=phone,
                defaults={
                    "full_name": name,
                    "date_of_birth": dob,
                    "gender": gender,
                    "blood_group": blood,
                    "email": mail,
                    "address": address,
                    "medical_history": history,
                },
            )
            patients.append(patient)

        for patient_idx, doctor_idx, is_primary, notes in ASSIGNMENTS:
            PatientDoctorMapping.objects.get_or_create(
                patient=patients[patient_idx],
                doctor=doctors[doctor_idx],
                defaults={"created_by": owner, "is_primary": is_primary, "notes": notes},
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: {Patient.objects.filter(created_by=owner).count()} patients, "
                f"{len(doctors)} doctors, "
                f"{PatientDoctorMapping.objects.filter(patient__created_by=owner).count()} assignments."
            )
        )
