========================
django-oscar-cybersource
========================

|  |license| |kit| |format| |downloads|

This package is to handle integration between django-oscar based e-commerce sites and `Cybersource Secure Acceptance Silent Order POST <http://apps.cybersource.com/library/documentation/dev_guides/Secure_Acceptance_SOP/Secure_Acceptance_SOP.pdf>`_.


Caveats
=======

1. Requires and `django-oscar>=1.1.1` and `django-oscar-api>=1.0.1`.
2. Your project must use PostgreSQL, since cybersource.models.CyberSourceReply uses an HStore field to log request data.
3. You must fork the Oscar payment app to add a mixin to the transaction model.


Installation
============


1. Install the `django-oscar-cybersource` packages.::

    $ pip install git+https://gitlab.com/thelabnyc/django-oscar-cybersource.git#r1.0.0

2. Add `cybersource` to your `INSTALLED_APPS`::

    # myproject/settings.py
    ...
    INSTALLED_APPS = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.postgres',
        ...
        'cybersource',
        ...
    ] + get_core_apps([
        ...
    ])
    ...

3. Add some attributes to `settings.py` to configure how the application should connect to Cybersource.::

    # myproject/settings.py

    # Create a Secure Acceptance profile using the Cybersource dashboard and enter the profile, access key, and secret key here
    CYBERSOURCE_PROFILE = ...
    CYBERSOURCE_ACCESS = ...
    CYBERSOURCE_SECRET = ...

    # Enter you Cybersource merchant ID and org ID as found in the dashboard
    CYBERSOURCE_MERCHANT_ID = ...
    CYBERSOURCE_ORG_ID = ...

    # This defaults to the test endpoint (https://testsecureacceptance.cybersource.com/silent/pay). Override with the prod endpoint for real transactions.
    CYBERSOURCE_ENDPOINT_PAY = ...

    # Upon successful authorization of the user's credit card, where should we send the user?
    # Enter the name of the thank you page view.
    CYBERSOURCE_REDIRECT_SUCCESS = 'checkout:thank-you'

    # Upon declined authorization of the user's credit card, where should we send the user?
    # Enter the name of view where they can try again.
    CYBERSOURCE_REDIRECT_FAIL = 'checkout:index'


4. Install extra fields on payment.models.Transaction (see also `How to fork Oscar apps <https://django-oscar.readthedocs.org/en/releases-1.1/topics/customisation.html#fork-the-oscar-app>`_).::

    # payment/models.py

    from cybersource.models import TransactionMixin
    from oscar.apps.payment.abstract_models import AbstractTransaction

    class Transaction(TransactionMixin, AbstractTransaction):
        pass

    from oscar.apps.payment.models import *  # noqa


5. Create and run migrations for the `payment` app.::

    $ python manage.py makemigrations payment
    $ python manage.py migrate


6. Add `cybersource.urls` to your URL config.::

    # myproject/urls.py
    from cybersource.app import application as cybersource

    ...
    urlpatterns = patterns('',
        ...
        url(r'^api/cybersource/', include(cybersource.urls)),
        ...
    )
    ...

7. In the Cybersource Secure Acceptance dashboard, set the customer response page to https://www.my-host.com/api/cybersource/cybersource-reply/. If using Decision Manager, set its notification URL to https://www.my-host.com/api/cybersource/decision-manager-review-notification/.

8. Include the device fingerprint code in your checkout interface.::

    {# One Pixel Image Code #}
    <p style="background:url({% url 'cybersource-fingerprint-redirect' url_type='img-1' %})"></p>
    <img src="{% url 'cybersource-fingerprint-redirect' url_type='img-2' %}" alt="">

    {# Flash Code #}
    <object type="application/x-shockwave-flash" data="{% url 'cybersource-fingerprint-redirect' url_type='flash' %}" width="1" height="1" id="thm_fp">
        <param name="movie" value="{% url 'cybersource-fingerprint-redirect' url_type='flash' %}" />
        <div></div>
    </object>

    {# JS Code #}
    <script src="{% url 'cybersource-fingerprint-redirect' url_type='js' %}" type="text/javascript"></script>


Usage
=====

Once a user has added items to his or her basket, your client-side application must perform the following steps to place an order using `SA SOP <http://apps.cybersource.com/library/documentation/dev_guides/Secure_Acceptance_SOP/Secure_Acceptance_SOP.pdf>`_.

1. Checkout using django-oscar-api-checkout's checkout view.
    a. This POST will freeze the basket and create an order.
2. The client JS should accept then call django-oscar-api-checkout's payment-statuses view, fill in the fields marked as editable, create a form tag with hidden elements for each field, append the form to the document, and submit it as a POST.
3. Cybersource will use the data from this POST to either accept or decline the authorization attempt on the user's credit card and redirect the user back to the customer response page, which we earlier set as https://www.my-host.com/api/cybersource/cybersource-reply/.
4. The Cybersource reply view will parse the response data and take action on it.
    1. Ensure the HMAC signature was valid, returning `400 Bad Request` is it isn't.
    2. Log the response data in the cybersource.CyberSourceReplyLog model.
    3. Check if the transaction ID already exists. If it does, redirect to `CYBERSOURCE_REDIRECT_SUCCESS` without doing anything else.
    4. Compare the reference number in the response data to the order number we generated and saved to the user's session in step 1. If it differs, throw an error and return `400 Bad Request`.
    5. Get the basket based on the ID we saved to the session in step 1. If it doesn't exist, throw an error and return `400 Bad Request`.
    6. If the decision was to decline the authorization:
        1. Add a message to the session using the text in `CYBERSOURCE_CARD_REJECT_ERROR`
        2. Mark the order as payment declined.
        3. Unfreeze the basket so that it is editable again.
        4. Redirect the user to `CYBERSOURCE_REDIRECT_FAIL`
    7. Create the related `cybersource.PaymentToken`, `payment.SourceType`, `payment.Source`, `payment.Transaction`, `order.PaymentEvent`, and `order.PaymentEventQuantity` models.
    8. Save the order ID to the session so that the `CYBERSOURCE_REDIRECT_SUCCESS` view can access it.
    9. Redirect the user to `CYBERSOURCE_REDIRECT_SUCCESS`.

While the flow described above is somewhat complex, it avoid payment information ever touching the server, thereby significantly lessening the weight of PCI compliance.

Example Checkout
================

Create an order::

    POST /api/checkout/

    {
        "guest_email": "foo@example.com",
        "basket": "/api/baskets/2387/",
        "shipping_method_code": "free-shipping",
        "shipping_address": {
            "country": "/api/countries/US/",
            "first_name": "Bob",
            "last_name": "Smith",
            "line1": "627 W 27th St",
            "postcode": "10001",
            "line4": "Manhattan",
            "state": "NY",
            "line2": "",
            "phone_number": "+1 (555) 555-5555"
        }
    }

The response code will indicate success or not. Now fetch the payment states endpoint.::

    GET `/api/checkout/payment-states`

The response to this POST will look something like this.::

    {
        "order_status": "Pending",
        "payment_method_statuses": {
            "cybersource": {
                "status": "Pending",
                "required_next_action": {
                    "url": "https://testsecureacceptance.cybersource.com/silent/pay",
                    "fields": [
                        {
                            "editable": false,
                            "value": "Smith",
                            "key": "ship_to_surname"
                        },
                        {
                            "editable": false,
                            "value": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
                            "key": "profile_id"
                        },
                        {
                            "editable": false,
                            "value": "12345678",
                            "key": "item_0_sku"
                        },
                        {
                            "editable": false,
                            "value": "card",
                            "key": "payment_method"
                        },
                        {
                            "editable": false,
                            "value": "2016-04-06T16:02:52Z",
                            "key": "signed_date_time"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "bill_to_phone"
                        },
                        {
                            "editable": false,
                            "value": "145995857289",
                            "key": "transaction_uuid"
                        },
                        {
                            "editable": false,
                            "value": "My Product",
                            "key": "item_0_name"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "bill_to_address_country"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "bill_to_forename"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "card_number"
                        },
                        {
                            "editable": false,
                            "value": "12345678910",
                            "key": "reference_number"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "bill_to_address_line1"
                        },
                        {
                            "editable": false,
                            "value": "8.8.8.8",
                            "key": "customer_ip_address"
                        },
                        {
                            "editable": false,
                            "value": "999.89",
                            "key": "item_0_unit_price"
                        },
                        {
                            "editable": false,
                            "value": "10001",
                            "key": "ship_to_address_postal_code"
                        },
                        {
                            "editable": false,
                            "value": "",
                            "key": "ship_to_address_line2"
                        },
                        {
                            "editable": false,
                            "value": "authorization,create_payment_token",
                            "key": "transaction_type"
                        },
                        {
                            "editable": false,
                            "value": "foo@example.com",
                            "key": "bill_to_email"
                        },
                        {
                            "editable": false,
                            "value": "Manhattan",
                            "key": "ship_to_address_city"
                        },
                        {
                            "editable": false,
                            "value": "en",
                            "key": "locale"
                        },
                        {
                            "editable": false,
                            "value": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                            "key": "access_key"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "bill_to_address_postal_code"
                        },
                        {
                            "editable": false,
                            "value": "card_number,bill_to_surname,card_cvn,bill_to_address_line1,bill_to_address_line2,card_expiry_date,bill_to_address_city,bill_to_address_state,bill_to_address_postal_code,bill_to_phone,card_type,bill_to_address_country,bill_to_forename",
                            "key": "unsigned_field_names"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "bill_to_surname"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "card_cvn"
                        },
                        {
                            "editable": false,
                            "value": "US",
                            "key": "ship_to_address_country"
                        },
                        {
                            "editable": false,
                            "value": "999.89",
                            "key": "amount"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "card_expiry_date"
                        },
                        {
                            "editable": false,
                            "value": "1",
                            "key": "line_item_count"
                        },
                        {
                            "editable": false,
                            "value": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
                            "key": "device_fingerprint_id"
                        },
                        {
                            "editable": false,
                            "value": "sxPsOiZ/uTrX/QgL1wzTVKP9jYrhc5e5gXLHvnfIvrQ=",
                            "key": "signature"
                        },
                        {
                            "editable": false,
                            "value": "627 W 27th St",
                            "key": "ship_to_address_line1"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "bill_to_address_line2"
                        },
                        {
                            "editable": false,
                            "value": "15555555555",
                            "key": "ship_to_phone"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "bill_to_address_state"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "card_type"
                        },
                        {
                            "editable": false,
                            "value": "USD",
                            "key": "currency"
                        },
                        {
                            "editable": false,
                            "value": "item_0_name,reference_number,ship_to_surname,ship_to_address_country,device_fingerprint_id,profile_id,item_0_sku,customer_ip_address,payment_method,item_0_unit_price,signed_date_time,ship_to_address_postal_code,line_item_count,ship_to_address_line2,currency,transaction_type,bill_to_email,ship_to_address_city,transaction_uuid,ship_to_address_line1,locale,access_key,signed_field_names,item_0_quantity,ship_to_phone,merchant_defined_data1,ship_to_address_state,amount,ship_to_forename,unsigned_field_names",
                            "key": "signed_field_names"
                        },
                        {
                            "editable": false,
                            "value": "1",
                            "key": "item_0_quantity"
                        },
                        {
                            "editable": true,
                            "value": "",
                            "key": "bill_to_address_city"
                        },
                        {
                            "editable": false,
                            "value": "NY",
                            "key": "ship_to_address_state"
                        },
                        {
                            "editable": false,
                            "value": "Bob",
                            "key": "ship_to_forename"
                        }
                    ]
                }
            }
        }
    }

The Javascript app should loop through the fields in the above response and fill in editable fields with user input. Using `underscore` and `jQuery`, this might look something like this::

    # Assume `response` is an object containing the above response data.

    # This information was collected from the user but never sent to our server
    var billing = {
        bill_to_address_city: 'Manhattan',
        bill_to_address_country: 'US',
        bill_to_address_line1: '627 W 27th St',
        bill_to_address_line2: '',
        bill_to_address_postal_code: '10001',
        bill_to_address_state: 'NY',
        bill_to_forename: 'Bob',
        bill_to_phone: '15555555555',
        bill_to_surname: 'Smith',
        card_cvn: '123',
        card_expiry_date: '12-2020',
        card_number: '4111111111111111',
        card_type: '001',
    }

    var form = $('<form style="display:none;">');
    form.attr('method', 'POST');
    form.attr('action', response.payment_method_statuses.cybersource.required_next_action.url);

    _.each(response.payment_method_statuses.cybersource.required_next_action.fields, function(data) {
        var field = $('<input type="hidden" />');
        if (data.editable && billing[data.key]) {
            data.value = billing[data.key];
        }

        field.attr('name', data.key);
        field.attr('value', data.value);
        field.appendTo(form);
    });

    form.appendTo('body');
    form.submit();



Changelog
=========

3.1.1
------------------
- Make sure amounts sent to Cybersource are always properly quantized

3.1.0
------------------
- Support flagging authorizations for review with Decision Manager
    - Transactions under review are marked with status `REVIEW`.
    - Adds new boolean property to payment.Transaction model: `transaction.is_pending_review`.
    - When handling an authorization that is pending review in Decision Manager, a note is added to the order.

3.0.5
------------------
- Fix IntegrityError sometimes thrown when processing a declined payment.

3.0.4
------------------
- Fix exception from typo in record_declined_authorization.

3.0.3
------------------
- Fix case-mismatch of payment source types.

3.0.2
------------------
- Add data migration to populate `CyberSourceReply.order` on rows from before 3.0.1.

3.0.1
------------------
- Added foreign key from `cybersource.CyberSourceReply` from `order.Order`.

3.0.0
------------------
- Change to two step SOP method with discrete get_token and authorization steps. This works around a bug in Cybersource's code which will leave a pending authorization on a user's card, even if the address verification or decision manager rejects the transaction. By doing the transaction in two phases, we can catch most AVN / DM rejections before the authorization is placed on the credit card. The downside is that the client must now perform 2 separate form posts to Cybersource.

2.0.0
------------------
- Refactor as a plugin to django-oscar-api-checkout to eliminate code not related to Cybersource.

1.0.3
------------------
- Make profile, access, and secret mandatory
- Upgrade to `django-oscar-api>=1.0.4` to get rid of the need for our custom empty basket check
- Make test coverage much more expansive

1.0.2
------------------
- README Updates
- Added tests for FingerprintRedirectView
- Fixed a bug in the img-2 redirect url

1.0.1
------------------
- README Updates

1.0.0 (2016-01-25)
------------------
- Initial release.



.. |license| image:: https://img.shields.io/pypi/l/django-oscar-cybersource.svg
    :target: https://pypi.python.org/pypi/django-oscar-cybersource
.. |kit| image:: https://badge.fury.io/py/django-oscar-cybersource.svg
    :target: https://pypi.python.org/pypi/django-oscar-cybersource
.. |format| image:: https://img.shields.io/pypi/format/django-oscar-cybersource.svg
    :target: https://pypi.python.org/pypi/django-oscar-cybersource
.. |downloads| image:: https://img.shields.io/pypi/dm/django-oscar-cybersource.svg?maxAge=2592000
    :target: https://pypi.python.org/pypi/django-oscar-cybersource
