"""The browser-facing half: a front door, sign-up, and the workspace it leads to.

Registration is open to anyone, so the interesting assertions are about
what a fresh account *cannot* reach.
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.doctors.models import Doctor
from apps.patients.models import Patient

from .factories import DEFAULT_PASSWORD, make_doctor, make_patient, make_user

User = get_user_model()

SIGNUP = {
    "name": "New Visitor",
    "email": "visitor@example.com",
    "password": "StrongPass!234",
    "confirm_password": "StrongPass!234",
}


class LandingPageTests(TestCase):
    def test_offers_both_ways_in(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/register/")
        self.assertContains(response, "/admin/login/")

    def test_points_at_the_api_documentation(self):
        self.assertContains(self.client.get("/"), "/api/docs/")


class RegistrationTests(TestCase):
    def test_login_page_offers_sign_up(self):
        """Arriving without an account should not be a dead end."""
        self.assertContains(self.client.get("/admin/login/"), "/register/")

    def test_form_renders(self):
        response = self.client.get("/register/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="confirm_password"')

    def test_signing_up_lands_in_the_admin(self):
        response = self.client.post("/register/", SIGNUP)
        self.assertRedirects(response, "/admin/", target_status_code=200)

    def test_new_account_is_staff_with_workspace_permissions(self):
        self.client.post("/register/", SIGNUP)
        user = User.objects.get(email="visitor@example.com")
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        for codename in ("add_patient", "change_patient", "view_patient",
                         "delete_patient", "view_doctor",
                         "add_patientdoctormapping"):
            with self.subTest(codename=codename):
                self.assertTrue(user.has_perm(f"{self._app(codename)}.{codename}"))

    @staticmethod
    def _app(codename):
        return {"patient": "patients", "doctor": "doctors",
                "patientdoctormapping": "mappings"}[codename.split("_", 1)[1]]

    def test_new_account_cannot_touch_users(self):
        self.client.post("/register/", SIGNUP)
        user = User.objects.get(email="visitor@example.com")
        self.assertFalse(user.has_perm("accounts.view_user"))
        self.assertFalse(user.has_perm("accounts.add_user"))

    def test_a_failure_part_way_leaves_no_account(self):
        """Otherwise the visitor's email collides with their own retry."""
        with mock.patch(
            "apps.accounts.web.grant_workspace_access",
            side_effect=RuntimeError("database went away"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post("/register/", SIGNUP)
        self.assertFalse(User.objects.filter(email=SIGNUP["email"]).exists())

    def test_email_must_be_unique(self):
        make_user(email="visitor@example.com")
        response = self.client.post("/register/", SIGNUP)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")

    def test_passwords_must_match(self):
        response = self.client.post("/register/", dict(SIGNUP, confirm_password="Different!234"))
        self.assertContains(response, "The two password fields do not match.")
        self.assertFalse(User.objects.filter(email="visitor@example.com").exists())

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            "/register/", dict(SIGNUP, password="abc", confirm_password="abc")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="visitor@example.com").exists())

    def test_already_signed_in_visitors_are_sent_on(self):
        user = make_user()
        self.client.force_login(user)
        self.assertRedirects(
            self.client.get("/register/"), "/admin/", target_status_code=302
        )


class WorkspaceIsolationTests(TestCase):
    """A registered account must see its own records and nobody else's."""

    @classmethod
    def setUpTestData(cls):
        cls.mine = make_user(email="mine@example.com", name="Mine")
        cls.theirs = make_user(email="theirs@example.com", name="Theirs")
        from apps.accounts.workspace import grant_workspace_access

        grant_workspace_access(cls.mine, allow_delete=True)
        cls.my_patient = make_patient(cls.mine, full_name="My Patient",
                                      phone="+919876500001")
        cls.their_patient = make_patient(cls.theirs, full_name="Their Patient",
                                         phone="+919876500002")
        cls.their_doctor = make_doctor(cls.theirs)

    def setUp(self):
        self.client.force_login(self.mine)

    def test_patient_list_shows_only_my_records(self):
        response = self.client.get("/admin/patients/patient/")
        self.assertContains(response, "My Patient")
        self.assertNotContains(response, "Their Patient")

    def test_another_users_patient_is_not_reachable(self):
        response = self.client.get(
            f"/admin/patients/patient/{self.their_patient.id}/change/"
        )
        self.assertEqual(response.status_code, 302)

    def test_the_user_table_is_closed(self):
        self.assertEqual(self.client.get("/admin/accounts/user/").status_code, 403)

    def test_index_does_not_offer_users(self):
        self.assertNotContains(self.client.get("/admin/"), "/admin/accounts/user/")

    def test_doctor_directory_is_shared_for_reading(self):
        """Otherwise a new account could not assign the doctors on file."""
        response = self.client.get("/admin/doctors/doctor/")
        self.assertContains(response, self.their_doctor.full_name)

    def test_another_users_doctor_opens_read_only(self):
        """Shared for reading, so the page renders -- without a save button."""
        response = self.client.get(
            f"/admin/doctors/doctor/{self.their_doctor.id}/change/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="_save"')

    def test_another_users_doctor_cannot_be_saved(self):
        response = self.client.post(
            f"/admin/doctors/doctor/{self.their_doctor.id}/change/",
            {"full_name": "Renamed By Someone Else"},
        )
        self.assertEqual(response.status_code, 403)
        self.their_doctor.refresh_from_db()
        self.assertNotEqual(self.their_doctor.full_name, "Renamed By Someone Else")

    def test_created_by_is_taken_from_the_session(self):
        response = self.client.post(
            "/admin/patients/patient/add/",
            {
                "full_name": "Added Via Admin",
                "date_of_birth": "1991-02-03",
                "gender": Patient.Gender.FEMALE,
                "blood_group": Patient.BloodGroup.O_POS,
                "phone": "+919876500003",
                "email": "", "address": "", "medical_history": "",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302, response.content[:400])
        added = Patient.objects.get(full_name="Added Via Admin")
        self.assertEqual(added.created_by, self.mine)

    def test_the_owner_field_is_not_on_the_form(self):
        """It links to the user table, which this account cannot read."""
        response = self.client.get("/admin/patients/patient/add/")
        self.assertNotContains(response, 'name="created_by"')


class SuperuserStillSeesEverythingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.boss = make_user(email="boss@example.com", name="Boss")
        cls.boss.is_staff = cls.boss.is_superuser = True
        cls.boss.save()
        cls.other = make_user(email="other@example.com", name="Other")
        make_patient(cls.other, full_name="Someone Elses", phone="+919876500004")

    def test_scoping_does_not_apply_to_superusers(self):
        self.client.force_login(self.boss)
        self.assertContains(
            self.client.get("/admin/patients/patient/"), "Someone Elses"
        )

    def test_superuser_form_still_has_the_owner_field(self):
        self.client.force_login(self.boss)
        self.assertContains(
            self.client.get("/admin/patients/patient/add/"), 'name="created_by"'
        )
