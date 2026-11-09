import json
import unittest

from openai_extractor import OpenAIExtractionClient, OpenAIExtractionConfig, OpenAIProviderError


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


def _chat_completion(content: dict) -> dict:
    return {"choices": [{"message": {"content": json.dumps(content)}}]}


class OpenAIExtractorConfigTests(unittest.TestCase):
    def test_rejects_missing_api_key(self):
        with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
            OpenAIExtractionConfig("").validate()

    def test_rejects_non_https_base_url(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            OpenAIExtractionConfig("key", base_url="http://api.openai.com").validate()


class OpenAIExtractionClientTests(unittest.TestCase):
    def test_extract_candidate_parses_structured_output(self):
        candidate = {
            "supplier": "Acme Corp",
            "invoiceNumber": "INV-1",
            "recipient": "acme@paypal.com",
            "amount": "100.00",
            "currency": "USD",
            "dueDate": "2026-12-01",
            "concept": "services",
            "evidence": {field: "excerpt" for field in ("supplier", "invoiceNumber", "recipient", "amount", "currency", "dueDate", "concept")},
        }
        captured = {}

        def opener(request, timeout):
            captured["request"] = request
            return FakeResponse(200, _chat_completion(candidate))

        client = OpenAIExtractionClient(OpenAIExtractionConfig("sk-test"), opener=opener)
        result = client.extract_candidate(source_content="Invoice text", source_kind="INVOICE")
        self.assertEqual(result, candidate)
        headers = {key.lower(): value for key, value in captured["request"].header_items()}
        self.assertEqual(headers["authorization"], "Bearer sk-test")
        body = json.loads(captured["request"].data)
        self.assertEqual(body["response_format"]["json_schema"]["schema"]["required"].count("evidence"), 1)
        self.assertEqual(body["response_format"]["json_schema"]["schema"]["properties"]["amount"]["maxLength"], 256)
        self.assertIn("max_tokens", body)

    def test_rejects_empty_source_content(self):
        client = OpenAIExtractionClient(OpenAIExtractionConfig("sk-test"), opener=lambda request, timeout: FakeResponse(200, {}))
        with self.assertRaisesRegex(ValueError, "source_content"):
            client.extract_candidate(source_content="   ", source_kind="INVOICE")

    def test_provider_error_preserves_status_and_body(self):
        def opener(request, timeout):
            return FakeResponse(429, {"error": {"message": "rate limited"}})

        client = OpenAIExtractionClient(OpenAIExtractionConfig("sk-test"), opener=opener)
        with self.assertRaises(OpenAIProviderError) as caught:
            client.extract_candidate(source_content="text", source_kind="INVOICE")
        self.assertEqual(caught.exception.status, 429)

    def test_non_json_content_is_a_provider_error_not_a_crash(self):
        def opener(request, timeout):
            return FakeResponse(200, {"choices": [{"message": {"content": "not json"}}]})

        client = OpenAIExtractionClient(OpenAIExtractionConfig("sk-test"), opener=opener)
        with self.assertRaises(OpenAIProviderError):
            client.extract_candidate(source_content="text", source_kind="INVOICE")


if __name__ == "__main__":
    unittest.main()
