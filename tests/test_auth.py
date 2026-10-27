from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .factories import DEFAULT_PASSWORD, make_user

User = get_user_model()


class RegisterTests(APITestCase):
    url = reverse("accounts:register")

    def test_registers_user_and_returns_tokens(self):
        payload = {
            "name": "Disha Gangwar",
            "email": "Disha@Example.com",
            "password": DEFAULT_PASSWORD,
            "confirm_password": DEFAULT_PASSWORD,
        }
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"]["tokens"])
        self.assertIn("refresh", response.data["data"]["tokens"])
        # Email is normalised to lowercase on the way in.
        self.assertEqual(response.data["data"]["user"]["email"], "disha@example.com")
        self.assertTrue(User.objects.get(email="disha@example.com").check_password(DEFAULT_PASSWORD))

    def test_password_is_never_echoed_back(self):
        response = self.client.post(
            self.url,
            {
                "name": "Disha Gangwar",
                "email": "d2@example.com",
                "password": DEFAULT_PASSWORD,
                "confirm_password": DEFAULT_PASSWORD,
            },
            format="json",
        )
        self.assertNotIn("password", str(response.data))

    def test_rejects_duplicate_email(self):
        make_user(email="taken@example.com")
        response = self.client.post(
            self.url,
            {
                "name": "Someone Else",
                "email": "taken@example.com",
                "password": DEFAULT_PASSWORD,
                "confirm_password": DEFAULT_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("email", response.data["error"]["details"])

    def test_rejects_mismatched_confirmation(self):
        response = self.client.post(
            self.url,
            {
                "name": "Disha Gangwar",
                "email": "mismatch@example.com",
                "password": DEFAULT_PASSWORD,
                "confirm_password": "SomethingElse!234",
                },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data["error"]["details"])

    def test_rejects_weak_password(self):
        response = self.client.post(
            self.url,
            {
                "name": "Disha Gangwar",
                "email": "weak@example.com",
                "password": "password",
                "confirm_password": "password",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data["error"]["details"])

    def test_rejects_missing_fields(self):
        response = self.client.post(self.url, {"email": "x@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field in ("name", "password", "confirm_password"):
            self.assertIn(field, response.data["error"]["details"])


class LoginTests(APITestCase):
    url = reverse("accounts:login")

    def setUp(self):
        self.user = make_user(email="login@example.com")

    def test_logs_in_with_valid_credentials(self):
        response = self.client.post(
            self.url,
            {"email": "login@example.com", "password": DEFAULT_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data["data"]["tokens"])

    def test_login_is_case_insensitive_on_email(self):
        response = self.client.post(
            self.url,
            {"email": "LOGIN@example.com", "password": DEFAULT_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_rejects_wrong_password_without_revealing_cause(self):
        wrong_password = self.client.post(
            self.url, {"email": "login@example.com", "password": "Nope!12345"}, format="json"
        )
        unknown_email = self.client.post(
            self.url, {"email": "ghost@example.com", "password": "Nope!12345"}, format="json"
        )
        self.assertEqual(wrong_password.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(unknown_email.status_code, status.HTTP_400_BAD_REQUEST)
        # Identical responses, so the endpoint cannot enumerate accounts.
        self.assertEqual(wrong_password.data["error"]["message"],
                         unknown_email.data["error"]["message"])

    def test_rejects_inactive_account(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.url,
            {"email": "login@example.com", "password": DEFAULT_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TokenTests(APITestCase):
    def setUp(self):
        self.user = make_user()

    def test_refresh_returns_new_access_token(self):
        login = self.client.post(
            reverse("accounts:login"),
            {"email": self.user.email, "password": DEFAULT_PASSWORD},
            format="json",
        )
        refresh = login.data["data"]["tokens"]["refresh"]
        response = self.client.post(
            reverse("accounts:token-refresh"), {"refresh": refresh}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_profile_requires_authentication(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["error"]["code"], "not_authenticated")

    def test_profile_returns_current_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["email"], self.user.email)

    def test_garbage_token_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
