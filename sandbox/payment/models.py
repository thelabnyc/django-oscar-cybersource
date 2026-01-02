from oscar.apps.payment.abstract_models import AbstractTransaction

from cybersource.models import TransactionMixin


class Transaction(TransactionMixin, AbstractTransaction):
    pass


from oscar.apps.payment.models import *  # type:ignore[assignment] # noqa
