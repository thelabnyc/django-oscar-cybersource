from cybersource.models import TransactionMixin
from oscar.apps.payment.abstract_models import AbstractTransaction


class Transaction(TransactionMixin, AbstractTransaction):
    pass


from oscar.apps.payment.models import *  # noqa
