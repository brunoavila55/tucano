from pathlib import Path

from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.ratelimit import enforce_rate_limit

from . import services
from .backup import run_postgres_backup
from .models import FeatureFlag, ModerationCase, Verification
from .validators import MAX_UPLOAD_SIZE_MB, validate_file_size

TINY_GIF = (
    b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00"
    b"\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


class ModerationCaseLifecycleTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.reporter = User.objects.create_user(username="denunciante", email="denunciante@example.com", password="senha-forte-123")
        self.reported = User.objects.create_user(username="denunciado", email="denunciado@example.com", password="senha-forte-123")
        self.moderator = User.objects.create_user(username="moderador", email="moderador@example.com", password="senha-forte-123", is_staff=True)

    def test_full_cycle_open_review_decide_suspend_appeal_approve_reactivates_account(self):
        case = services.open_case(self.reporter, self.reported, "Comportamento abusivo no chat")
        self.assertEqual(case.status, ModerationCase.Status.OPEN)

        services.start_review(case, self.moderator)
        case.refresh_from_db()
        self.assertEqual(case.status, ModerationCase.Status.UNDER_REVIEW)

        services.decide_case(case, self.moderator, ModerationCase.Decision.SUSPENSION, notes="Confirmado")
        case.refresh_from_db()
        self.reported.refresh_from_db()
        self.assertEqual(case.status, ModerationCase.Status.DECIDED)
        self.assertFalse(self.reported.is_active)

        self.assertIsNone(authenticate(username="denunciado", password="senha-forte-123"))

        services.appeal_case(case, self.reported, "Não fui eu, foi invasão de conta")
        case.refresh_from_db()
        self.assertEqual(case.status, ModerationCase.Status.APPEALED)

        services.resolve_appeal(case, self.moderator, approved=True, notes="Recurso procedente")
        case.refresh_from_db()
        self.reported.refresh_from_db()
        self.assertEqual(case.status, ModerationCase.Status.CLOSED)
        self.assertTrue(self.reported.is_active)
        self.assertIsNotNone(authenticate(username="denunciado", password="senha-forte-123"))

    def test_cannot_start_review_twice(self):
        case = services.open_case(self.reporter, self.reported, "Motivo")
        services.start_review(case, self.moderator)
        with self.assertRaises(ValidationError):
            services.start_review(case, self.moderator)

    def test_cannot_decide_a_case_twice(self):
        case = services.open_case(self.reporter, self.reported, "Motivo")
        services.decide_case(case, self.moderator, ModerationCase.Decision.WARNING)
        with self.assertRaises(ValidationError):
            services.decide_case(case, self.moderator, ModerationCase.Decision.DISMISSED)

    def test_only_reported_user_can_appeal(self):
        case = services.open_case(self.reporter, self.reported, "Motivo")
        services.decide_case(case, self.moderator, ModerationCase.Decision.SUSPENSION)
        with self.assertRaises(ValidationError):
            services.appeal_case(case, self.reporter, "Não fui eu")

    def test_cannot_appeal_case_that_is_not_decided(self):
        case = services.open_case(self.reporter, self.reported, "Motivo")
        with self.assertRaises(ValidationError):
            services.appeal_case(case, self.reported, "Ainda nem decidiram")

    def test_cannot_appeal_twice(self):
        case = services.open_case(self.reporter, self.reported, "Motivo")
        services.decide_case(case, self.moderator, ModerationCase.Decision.SUSPENSION)
        services.appeal_case(case, self.reported, "Motivo 1")
        with self.assertRaises(ValidationError):
            services.appeal_case(case, self.reported, "Motivo 2")

    def test_rejected_appeal_keeps_account_suspended(self):
        case = services.open_case(self.reporter, self.reported, "Motivo")
        services.decide_case(case, self.moderator, ModerationCase.Decision.SUSPENSION)
        services.appeal_case(case, self.reported, "Motivo")
        services.resolve_appeal(case, self.moderator, approved=False)
        self.reported.refresh_from_db()
        self.assertFalse(self.reported.is_active)


class ReportUserViewTest(TestCase):
    def test_authenticated_user_can_report_another(self):
        User = get_user_model()
        reporter = User.objects.create_user(username="rep1", email="rep1@example.com", password="senha-forte-123")
        reported = User.objects.create_user(username="rep2", email="rep2@example.com", password="senha-forte-123")
        self.client.force_login(reporter)

        response = self.client.post(
            reverse("moderation:report-user", args=[reported.pk]),
            {"reason": "Mensagens ofensivas", "context": "Conversa #1"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ModerationCase.objects.filter(reporter=reporter, reported_user=reported).exists())


class AppealViewTest(TestCase):
    def test_user_cannot_appeal_someone_elses_case(self):
        User = get_user_model()
        reporter = User.objects.create_user(username="rep3", email="rep3@example.com", password="senha-forte-123")
        reported = User.objects.create_user(username="rep4", email="rep4@example.com", password="senha-forte-123")
        outsider = User.objects.create_user(username="rep5", email="rep5@example.com", password="senha-forte-123")
        case = services.open_case(reporter, reported, "Motivo")
        services.decide_case(case, reporter, ModerationCase.Decision.WARNING)

        self.client.force_login(outsider)
        response = self.client.post(reverse("moderation:appeal-case", args=[case.pk]), {"reason": "Não sou eu"})
        self.assertEqual(response.status_code, 404)


class VerificationRequestTest(TestCase):
    def test_authenticated_user_can_submit_verification_request(self):
        User = get_user_model()
        user = User.objects.create_user(username="ver1", email="ver1@example.com", password="senha-forte-123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("moderation:verification-request"),
            {
                "document": SimpleUploadedFile("doc.gif", TINY_GIF, content_type="image/gif"),
                "consent": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        verification = Verification.objects.get(user=user)
        self.assertEqual(verification.status, Verification.Status.PENDING)
        self.assertTrue(verification.purpose)

    def test_request_without_consent_is_rejected(self):
        User = get_user_model()
        user = User.objects.create_user(username="ver2", email="ver2@example.com", password="senha-forte-123")
        self.client.force_login(user)

        response = self.client.post(
            reverse("moderation:verification-request"),
            {"document": SimpleUploadedFile("doc.gif", TINY_GIF, content_type="image/gif")},
        )
        self.assertEqual(response.status_code, 200)  # form_invalid re-renderiza
        self.assertFalse(Verification.objects.filter(user=user).exists())


class FeatureFlagTest(TestCase):
    def test_defaults_to_provided_default_when_flag_missing(self):
        self.assertTrue(FeatureFlag.is_active("nao-existe", default=True))
        self.assertFalse(FeatureFlag.is_active("nao-existe", default=False))

    def test_explicit_flag_overrides_default(self):
        FeatureFlag.objects.create(key="minha-flag", is_enabled=True)
        self.assertTrue(FeatureFlag.is_active("minha-flag", default=False))


class RateLimitTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_enforce_rate_limit_blocks_after_threshold(self):
        for _ in range(3):
            enforce_rate_limit("chave-teste-1", limit=3, window_seconds=60)
        with self.assertRaises(PermissionDenied):
            enforce_rate_limit("chave-teste-1", limit=3, window_seconds=60)

    def test_different_keys_have_independent_counters(self):
        for _ in range(3):
            enforce_rate_limit("chave-teste-2", limit=3, window_seconds=60)
        enforce_rate_limit("chave-teste-3", limit=3, window_seconds=60)  # não deve levantar

    def test_admin_login_is_rate_limited(self):
        for _ in range(10):
            self.client.post(reverse("admin:login"), {"username": "x", "password": "y"})
        response = self.client.post(reverse("admin:login"), {"username": "x", "password": "y"})
        self.assertEqual(response.status_code, 403)


class FileSizeValidatorTest(TestCase):
    def test_rejects_file_larger_than_limit(self):
        big_file = SimpleUploadedFile("big.gif", b"0" * (MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1))
        with self.assertRaises(ValidationError):
            validate_file_size(big_file)

    def test_accepts_file_within_limit(self):
        small_file = SimpleUploadedFile("small.gif", b"0" * 100)
        validate_file_size(small_file)


class BackupTest(TestCase):
    def test_run_postgres_backup_creates_a_non_empty_file(self):
        path = Path(run_postgres_backup())
        try:
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 0)
        finally:
            path.unlink(missing_ok=True)
