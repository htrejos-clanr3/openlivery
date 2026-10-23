"""SMTP mailer: skipped without configuration, sends when configured."""

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.services import mailer


class _FakeSMTP:
    def __init__(self, host, port, timeout=0):
        self.host = host
        self.port = port
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        self.tls = True

    def login(self, user, password):
        self.login_args = (user, password)

    def send_message(self, message):
        self.sent.append(message)


def _settings(**overrides):
    base = dict(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="bot@example.com",
        smtp_password="secret",
        smtp_from="bot@example.com",
        smtp_starttls=True,
        smtp_use_ssl=False,
        frontend_url="https://app.example",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_send_is_skipped_without_host(monkeypatch):
    monkeypatch.setattr(mailer, "get_settings", lambda: _settings(smtp_host=""))
    assert mailer.send_email(to="a@b.c", subject="x", text="y") is False


def test_send_delivers_when_configured(monkeypatch):
    fake = _FakeSMTP("smtp.example.com", 587)
    monkeypatch.setattr(mailer, "get_settings", lambda: _settings())
    monkeypatch.setattr(mailer.smtplib, "SMTP", lambda host, port, timeout=15: fake)
    assert mailer.send_email(to="a@b.c", subject="Hola", text="Cuerpo") is True
    assert fake.login_args == ("bot@example.com", "secret")
    assert fake.sent[0]["To"] == "a@b.c"
    assert fake.sent[0]["Subject"] == "Hola"


def test_reset_link_shape(monkeypatch):
    monkeypatch.setattr(mailer, "get_settings", lambda: _settings())
    assert mailer.password_reset_link("tok", "reset") == "https://app.example/login?token=tok&purpose=reset"


def test_forgot_password_sends_the_link(monkeypatch, authenticated_client: TestClient):
    sent = {}
    monkeypatch.setattr(mailer, "send_email", lambda **kwargs: sent.update(kwargs) or True)
    response = authenticated_client.post(
        "/api/auth/forgot-password",
        json={"email": "ana@prisma.com", "audience": "agency"},
    )
    assert response.status_code == 200, response.text
    assert sent["to"] == "ana@prisma.com"
    assert "purpose=reset" in sent["text"]
