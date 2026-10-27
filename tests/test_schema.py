"""The published OpenAPI schema must describe what the API really returns."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .factories import make_doctor, make_patient, make_user


class SchemaEndpointTests(APITestCase):
    def test_schema_is_public_and_served_as_yaml(self):
        response = self.client.get(reverse("schema"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("openapi", response.headers["Content-Type"])

    def test_swagger_ui_renders(self):
        response = self.client.get(reverse("swagger-ui"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/html", response.headers["Content-Type"])

    def test_redoc_renders(self):
        response = self.client.get(reverse("redoc"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_schema_generates_without_warnings(self):
        """A warning here means an endpoint is being documented by guesswork."""
        from drf_spectacular.drainage import GENERATOR_STATS
        from drf_spectacular.generators import SchemaGenerator

        GENERATOR_STATS.reset()   # otherwise an earlier generation leaks in
        with GENERATOR_STATS.silence():
            SchemaGenerator().get_schema(request=None, public=True)

        self.assertEqual(
            dict(GENERATOR_STATS._warn_cache), {},
            "drf-spectacular reported warnings while generating the schema",
        )
        self.assertEqual(
            dict(GENERATOR_STATS._error_cache), {},
            "drf-spectacular reported errors while generating the schema",
        )


class SchemaShapeTests(APITestCase):
    """Guards the envelope handling in core.schema against regressions."""

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()

    def setUp(self):
        from drf_spectacular.drainage import GENERATOR_STATS
        from drf_spectacular.generators import SchemaGenerator

        with GENERATOR_STATS.silence():
            self.schema = SchemaGenerator().get_schema(request=None, public=True)

    def body(self, path, method, code):
        content = self.schema["paths"][path][method]["responses"][code]["content"]
        schema = content["application/json"]["schema"]
        if "$ref" in schema:
            name = schema["$ref"].split("/")[-1]
            schema = self.schema["components"]["schemas"][name]
        return schema

    def properties(self, path, method, code):
        return list(self.body(path, method, code).get("properties", {}))

    def test_detail_responses_use_the_data_envelope(self):
        self.assertEqual(
            self.properties("/api/patients/{id}/", "get", "200"), ["success", "data"]
        )

    def test_write_responses_include_a_message(self):
        self.assertEqual(
            self.properties("/api/patients/", "post", "201"),
            ["success", "message", "data"],
        )

    def test_paginated_lists_are_not_wrapped_a_second_time(self):
        """The pagination class supplies the envelope; wrapping again would
        nest it under `data` and misdescribe every list endpoint."""
        props = self.properties("/api/patients/", "get", "200")
        self.assertIn("results", props)
        self.assertIn("count", props)
        self.assertNotIn("data", props)

    def test_delete_is_documented_as_200_with_a_message(self):
        responses = self.schema["paths"]["/api/patients/{id}/"]["delete"]["responses"]
        self.assertIn("200", responses)
        self.assertNotIn("204", responses)
        self.assertEqual(
            self.properties("/api/patients/{id}/", "delete", "200"),
            ["success", "message"],
        )

    def test_token_refresh_is_not_enveloped(self):
        """SimpleJWT's view returns a bare token payload, unlike the rest."""
        props = self.properties("/api/auth/refresh/", "post", "200")
        self.assertIn("access", props)
        self.assertNotIn("success", props)

    def test_auth_responses_document_user_and_tokens(self):
        body = self.body("/api/auth/login/", "post", "200")
        data_ref = body["properties"]["data"]["$ref"].split("/")[-1]
        data = self.schema["components"]["schemas"][data_ref]
        self.assertEqual(sorted(data["properties"]), ["tokens", "user"])

    def test_patient_doctors_route_documents_its_real_payload(self):
        body = self.body("/api/mappings/{id}/", "get", "200")
        data_ref = body["properties"]["data"]["$ref"].split("/")[-1]
        data = self.schema["components"]["schemas"][data_ref]
        self.assertEqual(sorted(data["properties"]), ["count", "doctors", "patient"])

    def test_error_envelopes_are_documented(self):
        responses = self.schema["paths"]["/api/patients/"]["post"]["responses"]
        for code in ("400", "401"):
            with self.subTest(code=code):
                props = self.properties("/api/patients/", "post", code)
                self.assertEqual(props, ["success", "error"])
        self.assertIn("details", self.body("/api/patients/", "post", "400")
                      ["properties"]["error"]["properties"])

    def test_public_endpoints_are_not_documented_as_requiring_auth(self):
        self.assertNotIn(
            "401", self.schema["paths"]["/api/auth/login/"]["post"]["responses"]
        )

    def test_every_api_path_is_documented(self):
        documented = set(self.schema["paths"])
        expected = {
            "/api/auth/register/", "/api/auth/login/", "/api/auth/refresh/",
            "/api/auth/profile/", "/api/patients/", "/api/patients/{id}/",
            "/api/doctors/", "/api/doctors/{id}/", "/api/mappings/",
            "/api/mappings/{id}/", "/api/mappings/by-patient/{id}/",
            "/api/mappings/assignment/{id}/",
        }
        self.assertEqual(expected - documented, set())
