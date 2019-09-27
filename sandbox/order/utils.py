from oscar.apps.order import utils
from oscarapicheckout.mixins import OrderCreatorMixin


class OrderCreator(OrderCreatorMixin, utils.OrderCreator):
    pass
