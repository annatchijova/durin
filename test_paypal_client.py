import base64
import json
import unittest

from paypal_client import PayPalProviderError, PayPalSandboxClient, PayPalSandboxConfig


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit=-1):
        return self._body


class PayPalClientTests(unittest.TestCase):
    def test_config_rejects_non_sandbox_endpoint(self):
        with self.assertRaisesRegex(ValueError, "Sandbox"):
            PayPalSandboxConfig("id", "secret", "https://api-m.paypal.com").validate()

    def test_client_gets_token_and_sends_stable_request_id(self):
        requests = []

        def opener(request, timeout):
            requests.append(request)
            if request.full_url.endswith("/v1/oauth2/token"):
                return FakeResponse(200, {"access_token": "sandbox-token"})
            return FakeResponse(201, {"batch_header": {"payout_batch_id": "B-1", "batch_status": "PENDING"}})

        client = PayPalSandboxClient(PayPalSandboxConfig("id", "secret", "http://127.0.0.1"), opener=opener)
        result = client.create_payout({"items": []}, "durin-request-1")
        self.assertEqual(result["batch_header"]["payout_batch_id"], "B-1")
        second_headers = {key.lower(): value for key, value in requests[1].header_items()}
        first_headers = {key.lower(): value for key, value in requests[0].header_items()}
        self.assertEqual(second_headers["paypal-request-id"], "durin-request-1")
        self.assertEqual(second_headers["authorization"], "Bearer sandbox-token")
        expected_basic = "Basic " + base64.b64encode(b"id:secret").decode()
        self.assertEqual(first_headers["authorization"], expected_basic)

    def test_provider_error_preserves_status_and_body(self):
        def opener(request, timeout):
            return FakeResponse(200, {"access_token": "sandbox-token"}) if request.full_url.endswith("token") else FakeResponse(503, {"name": "TEMPORARY_FAILURE"})

        client = PayPalSandboxClient(PayPalSandboxConfig("id", "secret", "http://localhost"), opener=opener)
        with self.assertRaises(PayPalProviderError) as caught:
            client.create_payout({}, "durin-request-2")
        self.assertEqual(caught.exception.status, 503)
        self.assertEqual(caught.exception.body, {"name": "TEMPORARY_FAILURE"})


if __name__ == "__main__":
    unittest.main()
