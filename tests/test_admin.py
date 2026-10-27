"""The admin should expose this project's models and nothing else."""

from django.contrib import admin
from django.contrib.auth.models import Group
from django.test import TestCase

from .factories import make_user


class AdminRegistrationTests(TestCase):
    def test_groups_are_not_registered(self):
        """Access is decided by record ownership, so groups are unused."""
        self.assertNotIn(Group, admin.site._registry)

    def test_project_models_are_registered(self):
        from apps.doctors.models import Doctor
        from apps.mappings.models import PatientDoctorMapping
        from apps.patients.models import Patient
        from django.contrib.auth import get_user_model

        for model in (get_user_model(), Patient, Doctor, PatientDoctorMapping):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)


class AdminPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user(email="staff@example.com", name="Staff")
        cls.admin.is_staff = True
        cls.admin.is_superuser = True
        cls.admin.save()

    def setUp(self):
        self.client.force_login(self.admin)

    def test_index_does_not_link_to_groups(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "/admin/auth/group/")

    def test_group_admin_page_is_gone(self):
        self.assertEqual(self.client.get("/admin/auth/group/").status_code, 404)

    def test_user_form_has_no_groups_field(self):
        response = self.client.get(f"/admin/accounts/user/{self.admin.id}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="groups"')

    def test_project_admin_pages_still_render(self):
        for url in (
            "/admin/",
            "/admin/accounts/user/",
            "/admin/patients/patient/",
            "/admin/doctors/doctor/",
            "/admin/mappings/patientdoctormapping/",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
