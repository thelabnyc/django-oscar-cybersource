from oscar.core.loading import get_model
from oscarapi.serializers.checkout import CheckoutSerializer as OscarCheckoutSerializer
from rest_framework import serializers

BillingAddress = get_model('order', 'BillingAddress')


class CheckoutSerializer(OscarCheckoutSerializer):
    order_number = None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs['basket'].num_items <= 0:
            raise serializers.ValidationError('Cannot checkout with empty basket')
        return attrs

    def create(self, validated_data):
        if not isinstance(validated_data['billing_address'], BillingAddress):
            validated_data['billing_address'] = BillingAddress(**validated_data['billing_address'])
        return super().create(validated_data)

    def generate_order_number(self, basket):
        if self.order_number:
            return self.order_number
        return super().generate_order_number(basket)
