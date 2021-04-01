.. _usage:

Usage
=====

Overview
--------

Once a user has added items to his or her basket, your client-side application must perform the following steps to place an order using `SA SOP <http://apps.cybersource.com/library/documentation/dev_guides/Secure_Acceptance_SOP/Secure_Acceptance_SOP.pdf>`_.

1. Checkout using django-oscar-api-checkout's checkout view.
    a. This POST will freeze the basket and create an order.
2. The client JS should then
   a. GET django-oscar-api-checkout's payment-states view
   b. Use the returned `payment_method_statuses` response data to build a request to Cybersource
     i. create a form tag with hidden elements for each `editable` field in `payment_method_statuses.cybersource.required_next_action.fields` and set form `action` to the url found in `payment_method_statuses.cybersource.required_next_action.url`
   c. appendthe form to the document, and submit it as a `POST`
3. Cybersource will use the data from this POST to either accept or decline the authorization attempt on the user's credit card and redirect the user back to the customer response page, which we earlier set as https://www.my-host.com/api/cybersource/cybersource-reply/.
4. The Cybersource reply view will parse the response data and take action on it.
    1. Ensure the HMAC signature was valid, returning `400 Bad Request` is it isn't.
    2. Log the response data in the cybersource.CyberSourceReplyLog model.
    3. Check if the transaction ID already exists. If it does, redirect to `CYBERSOURCE_REDIRECT_SUCCESS` without doing anything else.
    4. Compare the reference number in the response data to the order number we generated and saved to the user's session in step 1. If it differs, throw an error and return `400 Bad Request`.
    5. Get the basket based on the ID we saved to the session in step 1. If it doesn't exist, throw an error and return `400 Bad Request`.
    6. If the decision was to decline the authorization:
        1. Mark the order as payment declined.
        2. Unfreeze the basket so that it is editable again.
        3. Redirect the user to `CYBERSOURCE_REDIRECT_FAIL`
    7. Create the related `cybersource.PaymentToken`, `payment.SourceType`, `payment.Source`, `payment.Transaction`, `order.PaymentEvent`, and `order.PaymentEventQuantity` models.
    8. Save the order ID to the session so that the `CYBERSOURCE_REDIRECT_SUCCESS` view can access it.
    9. Redirect the user to `CYBERSOURCE_REDIRECT_SUCCESS`.

While the flow described above is somewhat complex, it avoid payment information ever touching the server, thereby significantly lessening the weight of PCI compliance.


Example Checkout Flow
---------------------

First, create an order.::

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

The response to this request will look something like this.::

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
