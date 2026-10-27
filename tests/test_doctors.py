from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.doctors.models import Doctor

from .factories import make_doctor, make_user


class DoctorAccessTests(APITestCase):
    def setUp(self):
        self.owner = make_user(email="owner@example.com")
        self.other = make_user(email="other@example.com", name="Other User")
        self.doctor = make_doctor(self.owner)
        self.list_url = reverse("doctors:doctor-list-create")
        self.detail_url = reverse("doctors:doctor-detail", args=[self.doctor.id])

    def test_endpoints_require_authentication(self):
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_directory_is_readable_by_any_authenticated_user(self):
        self.client.force_authenticate(self.other)

        self.assertEqual(self.client.get(self.list_url).data["count"], 1)
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_200_OK)

    def test_only_the_creator_may_modify_a_doctor(self):
        self.client.force_authenticate(self.other)

        patched = self.client.patch(self.detail_url, {"full_name": "Hacked"}, format="json")
        deleted = self.client.delete(self.detail_url)

        self.assertEqual(patched.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(deleted.status_code, status.HTTP_403_FORBIDDEN)
        self.doctor.refresh_from_db()
        self.assertEqual(self.doctor.full_name, "Rohan Kapoor")

    def test_creator_may_modify_a_doctor(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(self.detail_url, {"is_available": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["data"]["is_available"])


class DoctorCrudTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.list_url = reverse("doctors:doctor-list-create")

    def valid_payload(self, **overrides):
        payload = {
            "full_name": "Meera Iyer",
            "specialization": "NEUROLOGY",
            "license_number": "mci-20099",
            "email": "Meera.Iyer@Example.com",
            "phone": "+919823456789",
            "years_of_experience": 8,
            "consultation_fee": "1200.00",
        }
        payload.update(overrides)
        return payload

    def test_creates_doctor_and_normalises_fields(self):
        response = self.client.post(self.list_url, self.valid_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Doctor created successfully.")
        data = response.data["data"]
        self.assertEqual(data["license_number"], "MCI-20099")
        self.assertEqual(data["email"], "meera.iyer@example.com")
        self.assertEqual(data["specialization_display"], "Neurology")

    def test_retrieve_update_delete(self):
        created = self.client.post(self.list_url, self.valid_payload(), format="json")
        detail_url = reverse("doctors:doctor-detail", args=[created.data["data"]["id"]])

        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_200_OK)

        updated = self.client.put(
            detail_url, self.valid_payload(years_of_experience=9), format="json"
        )
        self.assertEqual(updated.data["data"]["years_of_experience"], 9)

        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_200_OK)
        self.assertFalse(Doctor.objects.filter(id=created.data["data"]["id"]).exists())

    def test_update_keeps_own_unique_values(self):
        """Re-submitting a doctor's own license/email must not self-collide."""
        created = self.client.post(self.list_url, self.valid_payload(), format="json")
        detail_url = reverse("doctors:doctor-detail", args=[created.data["data"]["id"]])

        response = self.client.put(
            detail_url, self.valid_payload(full_name="Meera R Iyer"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DoctorValidationTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.list_url = reverse("doctors:doctor-list-create")
        self.existing = make_doctor(self.user)

    def post(self, **overrides):
        payload = {
            "full_name": "Meera Iyer",
            "specialization": "NEUROLOGY",
            "license_number": "MCI-20099",
            "email": "meera@example.com",
            "phone": "+919823456789",
        }
        payload.update(overrides)
        return self.client.post(self.list_url, payload, format="json")

    def test_accepts_human_formatted_phone_and_normalises_it(self):
        response = self.post(phone="+91 98234-56789")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["phone"], "+919823456789")

    def test_rejects_malformed_phone(self):
        response = self.post(phone="not-a-phone")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", response.data["error"]["details"])

    def test_rejects_duplicate_license_number(self):
        response = self.post(license_number=self.existing.license_number)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("license_number", response.data["error"]["details"])

    def test_duplicate_license_check_is_case_insensitive(self):
        response = self.post(license_number=self.existing.license_number.lower())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("license_number", response.data["error"]["details"])

    def test_rejects_duplicate_email(self):
        response = self.post(email=self.existing.email)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data["error"]["details"])

    def test_rejects_unknown_specialization(self):
        response = self.post(specialization="ASTROLOGY")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("specialization", response.data["error"]["details"])

    def test_rejects_negative_experience(self):
        response = self.post(years_of_experience=-3)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("years_of_experience", response.data["error"]["details"])

    def test_rejects_implausible_experience(self):
        response = self.post(years_of_experience=99)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("years_of_experience", response.data["error"]["details"])

    def test_filter_by_specialization(self):
        response = self.client.get(self.list_url, {"specialization": "CARDIOLOGY"})
        self.assertEqual(response.data["count"], 1)
        response = self.client.get(self.list_url, {"specialization": "NEUROLOGY"})
        self.assertEqual(response.data["count"], 0)
