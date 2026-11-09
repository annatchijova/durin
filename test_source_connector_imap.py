import unittest

from source_connector_imap import IMAPSourceConfig, list_imap_sources


class FakeIMAPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.closed = False
        self.logged_out = False
        self.selected_readonly = None
        self._messages = {
            b"1": b"From: a@example.com\r\nSubject: Invoice A-1\r\n\r\nPlease pay 100.00 USD.",
            b"2": b"From: b@example.com\r\nSubject: Invoice A-2\r\n\r\nPlease pay 200.00 USD.",
        }

    def login(self, username, password):
        assert username and password
        return "OK", [b"logged in"]

    def select(self, mailbox, readonly=False):
        self.selected_readonly = readonly
        return "OK", [b"2"]

    def search(self, charset, criteria):
        return "OK", [b" ".join(self._messages.keys())]

    def fetch(self, message_id, parts):
        return "OK", [(message_id, self._messages[message_id])]

    def close(self):
        self.closed = True

    def logout(self):
        self.logged_out = True


class IMAPSourceConnectorTests(unittest.TestCase):
    def setUp(self):
        self.config = IMAPSourceConfig(host="imap.example.com", username="merchant", password="secret")

    def test_lists_messages_as_attested_email_sources(self):
        captured = {}

        def factory(host, port):
            client = FakeIMAPClient(host, port)
            captured["client"] = client
            return client

        sources = list_imap_sources(self.config, client_factory=factory)
        self.assertEqual(len(sources), 2)
        self.assertTrue(all(source["kind"] == "EMAIL" for source in sources))
        self.assertTrue(all(source["attestation"] for source in sources))
        self.assertTrue(captured["client"].closed)
        self.assertTrue(captured["client"].logged_out)

    def test_mailbox_is_opened_read_only(self):
        captured = {}

        def factory(host, port):
            client = FakeIMAPClient(host, port)
            captured["client"] = client
            return client

        list_imap_sources(self.config, client_factory=factory)
        self.assertTrue(captured["client"].selected_readonly)

    def test_max_messages_bounds_the_result(self):
        def factory(host, port):
            return FakeIMAPClient(host, port)

        sources = list_imap_sources(self.config, max_messages=1, client_factory=factory)
        self.assertEqual(len(sources), 1)

    def test_config_requires_host_username_and_password(self):
        with self.assertRaisesRegex(ValueError, "DURIN_IMAP_HOST"):
            IMAPSourceConfig(host="", username="u", password="p").validate()
        with self.assertRaisesRegex(ValueError, "DURIN_IMAP_USERNAME"):
            IMAPSourceConfig(host="h", username="", password="p").validate()

    def test_connection_is_closed_even_if_login_fails(self):
        class FailingClient(FakeIMAPClient):
            def login(self, username, password):
                raise ConnectionError("boom")

        captured = {}

        def factory(host, port):
            client = FailingClient(host, port)
            captured["client"] = client
            return client

        with self.assertRaises(ConnectionError):
            list_imap_sources(self.config, client_factory=factory)
        self.assertTrue(captured["client"].closed)
        self.assertTrue(captured["client"].logged_out)


if __name__ == "__main__":
    unittest.main()
