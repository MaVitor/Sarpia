from django.test import SimpleTestCase


class SaudeTests(SimpleTestCase):
    def test_saude_retorna_ok(self):
        resposta = self.client.get("/api/saude/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["status"], "ok")
