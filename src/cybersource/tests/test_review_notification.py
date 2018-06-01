from django.conf import settings
from django.urls import reverse
from django.test import TestCase
from oscar.core.loading import get_model
from oscar.test import factories
from .. import settings as pkg_settings

Order = get_model('order', 'Order')
Transaction = get_model('payment', 'Transaction')
SourceType = get_model('payment', 'SourceType')
Source = get_model('payment', 'Source')


ADDED_NOTE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE CaseManagementOrderStatus
  SYSTEM 'https://ebctest.cybersource.com/ebctest/reports/dtd/cmorderstatus_1_1.dtd'>
<CaseManagementOrderStatus
        Date="2016-08-24 16:28:33 GMT"
        MerchantID="somemerchant"
        Name="Case Management Order Status"
        Version="1.1"
        xmlns="http://reports.cybersource.com/reports/cmos/1.0">
    <Update MerchantReferenceNumber="117037850784" RequestID="4720554329436778504102">
        <OriginalDecision>REVIEW</OriginalDecision>
        <Reviewer>Bill</Reviewer>
        <Notes>
            <Note AddedBy="Bob" Comment="testing more stuff." Date="2016-08-24 16:28:33"/>
            <Note AddedBy="Tom" Comment="Took ownership." Date="2016-08-24 16:18:04"/>
            <Note AddedBy="Tom" Comment="Testing stuff." Date="2016-08-24 16:18:04"/>
        </Notes>
        <Queue>Review Queue</Queue>
        <Profile>Auths</Profile>
    </Update>
</CaseManagementOrderStatus>"""


ACCEPTED = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE CaseManagementOrderStatus
  SYSTEM 'https://ebctest.cybersource.com/ebctest/reports/dtd/cmorderstatus_1_1.dtd'>
<CaseManagementOrderStatus
        Date="2016-08-24 16:29:47 GMT"
        MerchantID="somemerchant"
        Name="Case Management Order Status"
        Version="1.1"
        xmlns="http://reports.cybersource.com/reports/cmos/1.0">
    <Update MerchantReferenceNumber="117037850784" RequestID="4720554329436778504102">
        <OriginalDecision>REVIEW</OriginalDecision>
        <NewDecision>ACCEPT</NewDecision>
        <Reviewer>Bill</Reviewer>
        <ReviewerComments>accepting this thing. | Billing and shipping addresses are the same.</ReviewerComments>
        <Notes>
            <Note AddedBy="Bob" Comment="testing more stuff." Date="2016-08-24 16:28:33"/>
            <Note AddedBy="Tom" Comment="Took ownership." Date="2016-08-24 16:18:04"/>
            <Note AddedBy="Tom" Comment="Testing stuff." Date="2016-08-24 16:18:04"/>
        </Notes>
        <Queue>Review Queue</Queue>
        <Profile>Auths</Profile>
    </Update>
</CaseManagementOrderStatus>"""


REJECTED = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE CaseManagementOrderStatus
  SYSTEM 'https://ebctest.cybersource.com/ebctest/reports/dtd/cmorderstatus_1_1.dtd'>
<CaseManagementOrderStatus
        Date="2016-08-24 16:31:26 GMT"
        MerchantID="somemerchant"
        Name="Case Management Order Status"
        Version="1.1"
        xmlns="http://reports.cybersource.com/reports/cmos/1.0">
    <Update MerchantReferenceNumber="117037850784" RequestID="4720554329436778504102">
        <OriginalDecision>REVIEW</OriginalDecision>
        <NewDecision>REJECT</NewDecision>
        <Reviewer>Bill</Reviewer>
        <ReviewerComments>some reason. | Order mis-typed.</ReviewerComments>
        <Notes>
            <Note AddedBy="Bill" Comment="Took ownership." Date="2016-08-24 16:31:25"/>
        </Notes>
        <Queue>Review Queue</Queue>
        <Profile>Auths</Profile>
    </Update>
</CaseManagementOrderStatus>"""


class DecisionManagerNotificationViewTest(TestCase):
    def test_add_note(self):
        order = factories.create_order(number='117037850784', status=settings.ORDER_STATUS_AUTHORIZED)

        stype, created = SourceType.objects.get_or_create(name='Test')
        source = Source.objects.create(
            order=order,
            source_type=stype,
            amount_allocated='99.99')
        transaction = Transaction.objects.create(
            source=source,
            txn_type=Transaction.AUTHORISE,
            amount='99.99',
            reference='4720554329436778504102',
            status='REVIEW')

        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, settings.ORDER_STATUS_AUTHORIZED)

        transaction = Transaction.objects.get(pk=transaction.pk)
        self.assertTrue(transaction.is_pending_review)
        self.assertEqual(transaction.status, 'REVIEW')

        url = reverse('cybersource-review-notification')
        data = {
            'content': ADDED_NOTE
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.notes.count(), 2)

        note = order.notes.get(message__startswith='[Decision Manager Wed Aug 24 16:18:04 2016]')
        self.assertEqual(note.note_type, 'System')
        self.assertEqual(note.message, (
            '[Decision Manager Wed Aug 24 16:18:04 2016] Tom added comment: Took ownership.\n'
            '[Decision Manager Wed Aug 24 16:18:04 2016] Tom added comment: Testing stuff.\n'
        ))

        note = order.notes.get(message__startswith='[Decision Manager Wed Aug 24 16:28:33 2016]')
        self.assertEqual(note.note_type, 'System')
        self.assertEqual(note.message, (
            '[Decision Manager Wed Aug 24 16:28:33 2016] Bob added comment: testing more stuff.\n'
        ))

        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, settings.ORDER_STATUS_AUTHORIZED)

        transaction = Transaction.objects.get(pk=transaction.pk)
        self.assertTrue(transaction.is_pending_review)
        self.assertEqual(transaction.status, 'REVIEW')


    def test_add_note_missing_order(self):
        url = reverse('cybersource-review-notification')
        data = {
            'content': ADDED_NOTE
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)


    def test_accepting_transaction(self):
        order = factories.create_order(number='117037850784', status=settings.ORDER_STATUS_AUTHORIZED)

        stype, created = SourceType.objects.get_or_create(name='Test')
        source = Source.objects.create(
            order=order,
            source_type=stype,
            amount_allocated='99.99')
        transaction = Transaction.objects.create(
            source=source,
            txn_type=Transaction.AUTHORISE,
            amount='99.99',
            reference='4720554329436778504102',
            status='REVIEW')

        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, settings.ORDER_STATUS_AUTHORIZED)

        transaction = Transaction.objects.get(pk=transaction.pk)
        self.assertTrue(transaction.is_pending_review)
        self.assertEqual(transaction.status, 'REVIEW')

        url = reverse('cybersource-review-notification')
        data = {
            'content': ACCEPTED
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.notes.count(), 3)

        note = order.notes.get(message__startswith='[Decision Manager Wed Aug 24 16:18:04 2016]')
        self.assertEqual(note.note_type, 'System')
        self.assertEqual(note.message, (
            '[Decision Manager Wed Aug 24 16:18:04 2016] Tom added comment: Took ownership.\n'
            '[Decision Manager Wed Aug 24 16:18:04 2016] Tom added comment: Testing stuff.\n'
        ))

        note = order.notes.get(message__startswith='[Decision Manager Wed Aug 24 16:28:33 2016]')
        self.assertEqual(note.note_type, 'System')
        self.assertEqual(note.message, (
            '[Decision Manager Wed Aug 24 16:28:33 2016] Bob added comment: testing more stuff.\n'
        ))

        note = order.notes.get(message__startswith='[Decision Manager]')
        self.assertEqual(note.note_type, 'System')
        self.assertEqual(note.message, (
            '[Decision Manager] Bill changed decision from REVIEW to ACCEPT.\n'
            '\n'
            'Comments: accepting this thing. | Billing and shipping addresses are the same.'
        ))

        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, settings.ORDER_STATUS_AUTHORIZED)

        transaction = Transaction.objects.get(pk=transaction.pk)
        self.assertFalse(transaction.is_pending_review)
        self.assertEqual(transaction.status, 'ACCEPT')


    def test_reject_transaction(self):
        order = factories.create_order(number='117037850784', status=settings.ORDER_STATUS_AUTHORIZED)

        stype, created = SourceType.objects.get_or_create(name='Test')
        source = Source.objects.create(
            order=order,
            source_type=stype,
            amount_allocated='99.99')
        transaction = Transaction.objects.create(
            source=source,
            txn_type=Transaction.AUTHORISE,
            amount='99.99',
            reference='4720554329436778504102',
            status='REVIEW')

        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, settings.ORDER_STATUS_AUTHORIZED)

        transaction = Transaction.objects.get(pk=transaction.pk)
        self.assertTrue(transaction.is_pending_review)
        self.assertEqual(transaction.status, 'REVIEW')

        url = reverse('cybersource-review-notification')
        data = {
            'content': REJECTED
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.notes.count(), 2)

        note = order.notes.get(message__startswith='[Decision Manager Wed Aug 24 16:31:25 2016]')
        self.assertEqual(note.note_type, 'System')
        self.assertEqual(note.message, (
            '[Decision Manager Wed Aug 24 16:31:25 2016] Bill added comment: Took ownership.\n'
        ))

        note = order.notes.get(message__startswith='[Decision Manager]')
        self.assertEqual(note.note_type, 'System')
        self.assertEqual(note.message, (
            '[Decision Manager] Bill changed decision from REVIEW to REJECT.\n'
            '\n'
            'Comments: some reason. | Order mis-typed.'
        ))

        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, settings.ORDER_STATUS_PAYMENT_DECLINED)

        transaction = Transaction.objects.get(pk=transaction.pk)
        self.assertFalse(transaction.is_pending_review)
        self.assertEqual(transaction.status, 'REJECT')

    def test_decision_manager_key_auth(self):
        order = factories.create_order(number='117037850784', status=settings.ORDER_STATUS_AUTHORIZED)

        stype, created = SourceType.objects.get_or_create(name='Test')
        source = Source.objects.create(
            order=order,
            source_type=stype,
            amount_allocated='99.99')
        transaction = Transaction.objects.create(
            source=source,
            txn_type=Transaction.AUTHORISE,
            amount='99.99',
            reference='4720554329436778504102',
            status='REVIEW')

        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, settings.ORDER_STATUS_AUTHORIZED)

        transaction = Transaction.objects.get(pk=transaction.pk)
        self.assertTrue(transaction.is_pending_review)
        self.assertEqual(transaction.status, 'REVIEW')

        # Set some auth keys for the DM view to use
        pkg_settings.DECISION_MANAGER_KEYS = (
            '12345',
            'abcdef',
        )

        # Request should fail, order should remain unchanged.
        url = reverse('cybersource-review-notification')
        data = {
            'content': REJECTED
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(order.notes.count(), 0)

        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, settings.ORDER_STATUS_AUTHORIZED)
        transaction = Transaction.objects.get(pk=transaction.pk)
        self.assertTrue(transaction.is_pending_review)
        self.assertEqual(transaction.status, 'REVIEW')

        # Request should success, order and transaction should be rejected.
        url = reverse('cybersource-review-notification') + '?key=abcdef'
        data = {
            'content': REJECTED
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.notes.count(), 2)

        note = order.notes.get(message__startswith='[Decision Manager Wed Aug 24 16:31:25 2016]')
        self.assertEqual(note.note_type, 'System')
        self.assertEqual(note.message, (
            '[Decision Manager Wed Aug 24 16:31:25 2016] Bill added comment: Took ownership.\n'
        ))

        note = order.notes.get(message__startswith='[Decision Manager]')
        self.assertEqual(note.note_type, 'System')
        self.assertEqual(note.message, (
            '[Decision Manager] Bill changed decision from REVIEW to REJECT.\n'
            '\n'
            'Comments: some reason. | Order mis-typed.'
        ))

        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.status, settings.ORDER_STATUS_PAYMENT_DECLINED)

        transaction = Transaction.objects.get(pk=transaction.pk)
        self.assertFalse(transaction.is_pending_review)
        self.assertEqual(transaction.status, 'REJECT')

        # Reset the keys to disable authentication
        pkg_settings.DECISION_MANAGER_KEYS = []
