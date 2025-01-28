from oscar.apps.payment import apps


class PaymentConfig(apps.PaymentConfig):
    name = "sandbox.payment"
