from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.mappings.models import PatientDoctorMapping

from .factories import make_doctor, make_patient, make_user


class MappingTests(APITestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user(email="other@example.com", name="Other User")
        self.patient = make_patient(self.user)
        self.doctor = make_doctor(self.user)
        self.client.force_authenticate(self.user)
        self.list_url = reverse("mappings:mapping-list-create")

    def assign(self, **overrides):
        payload = {"patient": self.patient.id, "doctor": self.doctor.id}
        payload.update(overrides)
        return self.client.post(self.list_url, payload, format="json")

    def test_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_assigns_doctor_to_patient(self):
        response = self.assign(notes="Referred for ECG.", is_primary=True)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mapping = PatientDoctorMapping.objects.get(id=response.data["data"]["id"])
        self.assertEqual(mapping.created_by, self.user)
        self.assertEqual(response.data["data"]["doctor_detail"]["full_name"], "Rohan Kapoor")
        self.assertEqual(response.data["message"], "Doctor assignment created successfully.")

    def test_lists_only_mappings_for_the_callers_patients(self):
        self.assign()
        foreign_patient = make_patient(self.other, phone="+919000000099", email="f@example.com")
        PatientDoctorMapping.objects.create(
            patient=foreign_patient, doctor=self.doctor, created_by=self.other
        )

        response = self.client.get(self.list_url)

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["patient"], self.patient.id)

    def test_cannot_assign_a_doctor_to_someone_elses_patient(self):
        foreign_patient = make_patient(self.other, phone="+919000000098", email="g@example.com")
        response = self.assign(patient=foreign_patient.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("patient", response.data["error"]["details"])

    def test_rejects_duplicate_assignment(self):
        self.assign()
        response = self.assign()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already assigned", str(response.data["error"]))

    def test_rejects_second_primary_doctor(self):
        self.assign(is_primary=True)
        second_doctor = make_doctor(
            self.user, license_number="MCI-55555", email="second@example.com"
        )
        response = self.assign(doctor=second_doctor.id, is_primary=True)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_primary", response.data["error"]["details"])

    def test_allows_several_non_primary_doctors(self):
        self.assign()
        second_doctor = make_doctor(
            self.user, license_number="MCI-66666", email="third@example.com"
        )
        self.assertEqual(self.assign(doctor=second_doctor.id).status_code,
                         status.HTTP_201_CREATED)

    def test_rejects_unknown_patient_or_doctor(self):
        self.assertEqual(self.assign(patient=999999).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.assign(doctor=999999).status_code, status.HTTP_400_BAD_REQUEST)


class PatientMappingLookupTests(APITestCase):
    """GET /api/mappings/<patient_id>/ and DELETE /api/mappings/<id>/."""

    def setUp(self):
        self.user = make_user()
        self.other = make_user(email="other@example.com", name="Other User")
        self.patient = make_patient(self.user)
        self.doctor = make_doctor(self.user)
        self.mapping = PatientDoctorMapping.objects.create(
            patient=self.patient, doctor=self.doctor, created_by=self.user
        )
        self.client.force_authenticate(self.user)

    def test_get_returns_every_doctor_for_that_patient(self):
        second_doctor = make_doctor(
            self.user, license_number="MCI-77777", email="fourth@example.com"
        )
        PatientDoctorMapping.objects.create(
            patient=self.patient, doctor=second_doctor, created_by=self.user
        )

        response = self.client.get(reverse("mappings:mapping-detail", args=[self.patient.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 2)
        self.assertEqual(response.data["data"]["patient"]["id"], self.patient.id)

    def test_get_uses_patient_id_not_mapping_id(self):
        """The alias route must agree with the overloaded one."""
        overloaded = self.client.get(reverse("mappings:mapping-detail", args=[self.patient.id]))
        alias = self.client.get(reverse("mappings:mappings-by-patient", args=[self.patient.id]))
        self.assertEqual(overloaded.data["data"], alias.data["data"])

    def test_get_for_another_users_patient_is_404(self):
        foreign = make_patient(self.other, phone="+919000000097", email="h@example.com")
        response = self.client.get(reverse("mappings:mapping-detail", args=[foreign.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_removes_the_assignment_by_mapping_id(self):
        response = self.client.delete(
            reverse("mappings:mapping-detail", args=[self.mapping.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PatientDoctorMapping.objects.filter(id=self.mapping.id).exists())

    def test_delete_cannot_touch_another_users_mapping(self):
        foreign_patient = make_patient(self.other, phone="+919000000096", email="i@example.com")
        foreign_mapping = PatientDoctorMapping.objects.create(
            patient=foreign_patient, doctor=self.doctor, created_by=self.other
        )

        response = self.client.delete(
            reverse("mappings:mapping-detail", args=[foreign_mapping.id])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(PatientDoctorMapping.objects.filter(id=foreign_mapping.id).exists())

    def test_deleting_a_patient_cascades_to_its_mappings(self):
        self.patient.delete()
        self.assertFalse(PatientDoctorMapping.objects.filter(id=self.mapping.id).exists())

    def test_deleting_a_doctor_cascades_to_its_mappings(self):
        self.doctor.delete()
        self.assertFalse(PatientDoctorMapping.objects.filter(id=self.mapping.id).exists())
