import json
import unittest

from openai_extractor import OpenAIExtractionClient, OpenAIExtractionConfig
from openai_chat_client import OpenAIChatClient


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


def _chat_completion(content) -> dict:
    return {"choices": [{"message": {"content": content if isinstance(content, str) else json.dumps(content)}}]}


class OpenAIChatClientTests(unittest.TestCase):
    def _client(self, opener):
        extraction_client = OpenAIExtractionClient(OpenAIExtractionConfig("sk-test"), opener=opener)
        return OpenAIChatClient(extraction_client)

    def test_interpret_query_returns_structured_hints(self):
        hints = {"monthsBack": 6, "counterpartyHint": "Acme", "amountHint": "450.00", "keywords": ["consulting"]}
        chat = self._client(lambda request, timeout: FakeResponse(200, _chat_completion(hints)))
        result = chat.interpret_query("Acme says we owe them 450 for consulting, sometime in the last 6 months")
        self.assertEqual(result, hints)

    def test_interpret_query_rejects_empty_question(self):
        chat = self._client(lambda request, timeout: FakeResponse(200, {}))
        with self.assertRaisesRegex(ValueError, "question"):
            chat.interpret_query("   ")

    def test_narrate_results_sends_only_the_real_transactions(self):
        captured = {}

        def opener(request, timeout):
            captured["body"] = json.loads(request.data)
            return FakeResponse(200, _chat_completion("Found one matching payment, TXN-1, 450.00 USD on 2026-05-01."))

        chat = self._client(opener)
        transactions = [{"transactionId": "TXN-1", "amountValue": "450.00", "currency": "USD", "date": "2026-05-01"}]
        answer = chat.narrate_results(question="Did we pay Acme 450?", transactions=transactions)
        self.assertIn("TXN-1", answer)
        sent_content = json.loads(captured["body"]["messages"][1]["content"])
        self.assertEqual(sent_content["transactions"], transactions)

    def test_narrate_results_with_no_matches_still_calls_model_with_empty_array(self):
        captured = {}

        def opener(request, timeout):
            captured["body"] = json.loads(request.data)
            return FakeResponse(200, _chat_completion("No matching payment was found in the searched period."))

        chat = self._client(opener)
        answer = chat.narrate_results(question="Did we pay Acme 450?", transactions=[])
        self.assertIn("No matching", answer)
        sent_content = json.loads(captured["body"]["messages"][1]["content"])
        self.assertEqual(sent_content["transactions"], [])


if __name__ == "__main__":
    unittest.main()
