"""Web forms for the self-service pages.

The rules mirror `RegisterSerializer` so that signing up through the
website and through the API accept and reject exactly the same input.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class RegistrationForm(forms.Form):
    name = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, strip=False)
    confirm_password = forms.CharField(
        widget=forms.PasswordInput, strip=False, label="Confirm password"
    )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters long.")
        return name

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password")
        if password and cleaned.get("confirm_password") != password:
            self.add_error("confirm_password", "The two password fields do not match.")
        if password:
            # Validate against the real field values so the similarity
            # check sees the name and email the account will have.
            candidate = User(name=cleaned.get("name", ""), email=cleaned.get("email", ""))
            try:
                validate_password(password, user=candidate)
            except forms.ValidationError as exc:
                self.add_error("password", exc)
        return cleaned

    def save(self):
        return User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            name=self.cleaned_data["name"],
        )
