from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.patients.models import Patient

from .factories import make_patient, make_user


class PatientAccessTests(APITestCase):
    def setUp(self):
        self.owner = make_user(email="owner@example.com")
        self.other = make_user(email="other@example.com", name="Other User")
        self.patient = make_patient(self.owner)
        self.list_url = reverse("patients:patient-list-create")
        self.detail_url = reverse("patients:patient-detail", args=[self.patient.id])

    def test_all_patient_endpoints_require_authentication(self):
        for method, url in [
            ("get", self.list_url),
            ("post", self.list_url),
            ("get", self.detail_url),
            ("put", self.detail_url),
            ("delete", self.detail_url),
        ]:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_only_the_callers_patients(self):
        make_patient(self.other, phone="+919000000001", email="theirs@example.com")
        self.client.force_authenticate(self.owner)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.patient.id)

    def test_other_users_patient_is_not_found_rather_than_forbidden(self):
        self.client.force_authenticate(self.other)
        response = self.client.get(self.detail_url)
        # 404 not 403: the existence of another user's record is not disclosed.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_user_cannot_update_or_delete(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.patch(self.detail_url, {"full_name": "Hacked"}, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(self.detail_url).status_code, status.HTTP_404_NOT_FOUND
        )
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.full_name, "Asha Mehta")


class PatientCrudTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.list_url = reverse("patients:patient-list-create")

    def valid_payload(self, **overrides):
        payload = {
            "full_name": "Vikram Rao",
            "date_of_birth": "1985-03-22",
            "gender": "MALE",
            "blood_group": "B+",
            "phone": "+919845012345",
            "email": "vikram@example.com",
            "address": "44 MG Road, Bengaluru",
            "medical_history": "Type 2 diabetes.",
        }
        payload.update(overrides)
        return payload

    def test_creates_patient_owned_by_caller(self):
        response = self.client.post(self.list_url, self.valid_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Patient created successfully.")
        patient = Patient.objects.get(id=response.data["data"]["id"])
        self.assertEqual(patient.created_by, self.user)

    def test_created_by_in_request_body_is_ignored(self):
        intruder = make_user(email="intruder@example.com", name="Intruder")
        response = self.client.post(
            self.list_url, self.valid_payload(created_by=intruder.id), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Patient.objects.get(id=response.data["data"]["id"]).created_by, self.user)

    def test_age_is_derived_from_date_of_birth(self):
        thirty_years_ago = timezone.localdate() - timedelta(days=365 * 30 + 8)
        response = self.client.post(
            self.list_url,
            self.valid_payload(date_of_birth=thirty_years_ago.isoformat()),
            format="json",
        )
        self.assertEqual(response.data["data"]["age"], 30)

    def test_retrieve_update_and_delete(self):
        created = self.client.post(self.list_url, self.valid_payload(), format="json")
        detail_url = reverse("patients:patient-detail", args=[created.data["data"]["id"]])

        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_200_OK)

        updated = self.client.put(
            detail_url, self.valid_payload(full_name="Vikram S Rao"), format="json"
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["data"]["full_name"], "Vikram S Rao")

        patched = self.client.patch(detail_url, {"blood_group": "O-"}, format="json")
        self.assertEqual(patched.data["data"]["blood_group"], "O-")

        self.assertEqual(self.client.delete(detail_url).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_patient_returns_structured_404(self):
        response = self.client.get(reverse("patients:patient-detail", args=[999999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["error"]["code"], "not_found")


class PatientValidationTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(self.user)
        self.list_url = reverse("patients:patient-list-create")

    def post(self, **overrides):
        payload = {
            "full_name": "Vikram Rao",
            "date_of_birth": "1985-03-22",
            "gender": "MALE",
            "phone": "+919845012345",
        }
        payload.update(overrides)
        return self.client.post(self.list_url, payload, format="json")

    def test_rejects_future_date_of_birth(self):
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()
        response = self.post(date_of_birth=tomorrow)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_of_birth", response.data["error"]["details"])

    def test_rejects_implausible_date_of_birth(self):
        response = self.post(date_of_birth="1850-01-01")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_of_birth", response.data["error"]["details"])

    def test_rejects_invalid_gender_choice(self):
        response = self.post(gender="ROBOT")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("gender", response.data["error"]["details"])

    def test_accepts_human_formatted_phone_and_normalises_it(self):
        """Separators are stripped before the format check runs."""
        for entered in ["+91 98450-12345", "+91 (98450) 12345", "+91.98450.12345"]:
            with self.subTest(entered=entered):
                Patient.objects.all().delete()
                response = self.client.post(
                    self.list_url,
                    {
                        "full_name": "Vikram Rao",
                        "date_of_birth": "1985-03-22",
                        "gender": "MALE",
                        "phone": entered,
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(response.data["data"]["phone"], "+919845012345")

    def test_normalised_phone_still_trips_the_duplicate_check(self):
        make_patient(self.user, phone="+919845012345")
        response = self.post(phone="+91 98450-12345")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", response.data["error"]["details"])

    def test_rejects_malformed_phone(self):
        response = self.post(phone="not-a-phone")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", response.data["error"]["details"])

    def test_rejects_duplicate_phone_for_same_user(self):
        make_patient(self.user, phone="+919845012345")
        response = self.post()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", response.data["error"]["details"])

    def test_same_phone_allowed_across_different_users(self):
        other = make_user(email="other@example.com", name="Other")
        make_patient(other, phone="+919845012345")
        self.assertEqual(self.post().status_code, status.HTTP_201_CREATED)

    def test_trims_and_collapses_whitespace_in_name(self):
        response = self.post(full_name="  Vikram   Rao  ")
        self.assertEqual(response.data["data"]["full_name"], "Vikram Rao")

    def test_rejects_too_short_name(self):
        response = self.post(full_name="V")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("full_name", response.data["error"]["details"])


class PatientFilterTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(self.user)
        make_patient(self.user, full_name="Asha Mehta", phone="+919000000011",
                     gender="FEMALE", email="asha@example.com")
        make_patient(self.user, full_name="Bharat Singh", phone="+919000000012",
                     gender="MALE", email="bharat@example.com")
        self.list_url = reverse("patients:patient-list-create")

    def test_filter_by_gender(self):
        response = self.client.get(self.list_url, {"gender": "MALE"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["full_name"], "Bharat Singh")

    def test_search_by_name(self):
        response = self.client.get(self.list_url, {"search": "Asha"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["full_name"], "Asha Mehta")

    def test_search_also_covers_phone(self):
        response = self.client.get(self.list_url, {"search": "919000000012"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["full_name"], "Bharat Singh")

    def test_ordering_by_name(self):
        response = self.client.get(self.list_url, {"ordering": "full_name"})
        names = [row["full_name"] for row in response.data["results"]]
        self.assertEqual(names, sorted(names))
