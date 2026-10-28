"""The two browser-facing pages: a front door and a sign-up form.

Everything else in this project answers JSON. These exist so a visitor
can get an account without being handed shared credentials, and land
somewhere they can actually use.
"""

from django.contrib import admin
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import RegistrationForm
from .workspace import grant_workspace_access


class LandingView(TemplateView):
    """Front door, offering the two ways in plus the API documentation."""

    template_name = "landing.html"


class RegisterPageView(FormView):
    template_name = "registration/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("admin:index")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # Borrow the admin's chrome so the page the visitor arrives from
        # and the one they land on look like the same site.
        context = admin.site.each_context(self.request)
        context.update(super().get_context_data(**kwargs))
        context["title"] = "Create an account"
        return context

    def form_valid(self, form):
        user = form.save()
        # Their own records only, so deleting them harms nobody else.
        grant_workspace_access(user, allow_delete=True)
        login(self.request, user)
        return super().form_valid(form)
