from django.db import connection
from django.db.models import Q
from django.test import TestCase

from ..models import CyberSourceReply, PaymentToken, SecureAcceptanceProfile
from .factories import build_accepted_token_reply_data


class PaymentTokenTest(TestCase):
    def test_log_data_parsing(self):
        data = build_accepted_token_reply_data("S123456789", "")
        log = CyberSourceReply.objects.create(
            data=data,
            auth_avs_code=data.get("auth_avs_code"),
            auth_code=data.get("auth_code"),
            auth_response=data.get("auth_response"),
            auth_trans_ref_no=data.get("auth_trans_ref_no"),
            decision=data.get("decision"),
            message=data.get("message"),
            reason_code=data.get("reason_code"),
            req_bill_to_address_postal_code=data.get("req_bill_to_address_postal_code"),
            req_bill_to_forename=data.get("req_bill_to_forename"),
            req_bill_to_surname=data.get("req_bill_to_surname"),
            req_card_expiry_date=data.get("req_card_expiry_date"),
            req_reference_number=data.get("req_reference_number"),
            req_transaction_type=data.get("req_transaction_type"),
            req_transaction_uuid=data.get("req_transaction_uuid"),
            request_token=data.get("request_token"),
            transaction_id=data.get("transaction_id"),
        )
        token = PaymentToken.objects.create(
            log=log,
            token=data["payment_token"],
            masked_card_number=data["req_card_number"],
            card_type=data["req_card_type"],
        )

        self.assertEqual(token.card_type_name, "Visa")
        self.assertEqual(token.billing_zip_code, "10001")
        self.assertEqual(token.expiry_month, "12")
        self.assertEqual(token.expiry_year, "2020")
        self.assertEqual(token.card_last4, "1111")
        self.assertEqual(token.card_holder, "Bob Smith")


class SecureAcceptanceProfileTest(TestCase):
    def setUp(self):
        SecureAcceptanceProfile.objects.create(
            hostname="foo.example.com",
            profile_id="a",
            access_key="",
            secret_key="",
            is_default=False,
        )
        SecureAcceptanceProfile.objects.create(
            hostname="bar.example.com",
            profile_id="b",
            access_key="",
            secret_key="",
            is_default=False,
        )
        SecureAcceptanceProfile.objects.create(
            hostname="www.example.com",
            profile_id="c",
            access_key="",
            secret_key="",
            is_default=True,
        )

    def test_get_profile(self):
        profile = SecureAcceptanceProfile.get_profile("foo.example.com")
        self.assertEqual(profile.profile_id, "a")

        profile = SecureAcceptanceProfile.get_profile("bar.example.com")
        self.assertEqual(profile.profile_id, "b")

        profile = SecureAcceptanceProfile.get_profile("www.example.com")
        self.assertEqual(profile.profile_id, "c")

    def test_default_fallback(self):
        profile = SecureAcceptanceProfile.get_profile("baz.example.com")
        self.assertEqual(profile.profile_id, "c")

    def test_no_profiles(self):
        SecureAcceptanceProfile.objects.all().delete()
        profile = SecureAcceptanceProfile.get_profile("www.example.com")
        self.assertEqual(profile.profile_id, "2A37F989-C8B2-4FEF-ACCF-2562577780E2")


class CyberSourceReplyScrubIndexTest(TestCase):
    """Test the partial index on CyberSourceReply for data scrubbing performance."""

    def test_model_has_scrub_candidates_index(self) -> None:
        """The model Meta should declare the partial index."""
        indexes = CyberSourceReply._meta.indexes
        matching = [i for i in indexes if i.name == "cybersource_reply_scrub_cands"]
        self.assertEqual(len(matching), 1)
        idx = matching[0]
        self.assertEqual(idx.fields, ["date_created"])
        self.assertEqual(idx.condition, ~Q(data={}))

    def test_scrub_candidates_index_exists_in_database(self) -> None:
        """The partial index should actually exist in the database."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'cybersource_cybersourcereply' "
                "AND indexname = 'cybersource_reply_scrub_cands'"
            )
            rows = cursor.fetchall()
        self.assertEqual(len(rows), 1)

    def test_scrub_query_excludes_already_empty_rows(self) -> None:
        """Rows with data={} should not appear in the scrub candidate query."""
        # Create a reply with data, then scrub it
        data = build_accepted_token_reply_data("ORDER-1", "")
        reply_with_data = CyberSourceReply.objects.create(data=data)
        reply_already_scrubbed = CyberSourceReply.objects.create(data={})

        candidates = CyberSourceReply.objects.exclude(data={})
        self.assertIn(reply_with_data, candidates)
        self.assertNotIn(reply_already_scrubbed, candidates)
