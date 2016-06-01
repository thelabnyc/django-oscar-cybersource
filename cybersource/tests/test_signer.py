from django.test import TestCase
from django.test.client import RequestFactory
from ..signature import SecureAcceptanceSigner


class SignerTest(TestCase):
    def test_sign(self):
        signer = SecureAcceptanceSigner()

        # Baseline
        signer.secret_key = 'FOO'
        signature = signer.sign({ 'foo': 'bar', 'baz': 'bat' }, ('foo', 'baz'))
        self.assertEqual(signature, b'IVMC7Aj8pDKwLx+0eNfIfoQAHvViiLeavLyYatCtB+c=')

        # Change field order
        signature = signer.sign({ 'foo': 'bar', 'baz': 'bat' }, ('baz', 'foo'))
        self.assertEqual(signature, b'5Gw1ffUlVU9Cm0tTa/nzhQ81Bc6/SDqz/tEP5VyMzkk=')

        # Change key
        signer.secret_key = 'SECRET'
        signature = signer.sign({ 'foo': 'bar', 'baz': 'bat' }, ('foo', 'baz'))
        self.assertEqual(signature, b'FvjC1PIhxuaLipTbRDw9UXL6F58t9Hyj12HLHiYoOD0=')

    def test_verify(self):
        rf = RequestFactory()
        signer = SecureAcceptanceSigner()

        # Baseline
        signer.secret_key = 'FOO'
        request = rf.post('/', {
            'signed_field_names': 'foo,baz',
            'signature': 'IVMC7Aj8pDKwLx+0eNfIfoQAHvViiLeavLyYatCtB+c=',
            'foo': 'bar',
            'baz': 'bat',
        })
        self.assertTrue( signer.verify_request(request) )

        # Bad signature given
        request = rf.post('/', {
            'signed_field_names': 'foo,baz',
            'signature': 'IVMC7Aj8pDKwLx+0eNfIfoQAHvViiLeavLyYatCtB',
            'foo': 'bar',
            'baz': 'bat',
        })
        self.assertFalse( signer.verify_request(request) )
