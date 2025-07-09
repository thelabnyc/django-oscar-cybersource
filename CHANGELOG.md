# Changes

## v9.3.0 (2025-07-09)

### Feat

- test against django 5.2

### Fix

- **deps**: update dependency lxml to v6
- **deps**: update dependency cryptography to v45
- update docker image tag format
- **deps**: update dependency django-oscar to >=4.0,<4.1
- **deps**: update dependency phonenumbers to ^9.0.3
- **deps**: update dependency pydantic to ^2.11.3
- **deps**: update dependency lxml to ^5.3.2
- **deps**: update dependency thelabdb to >=0.5.0
- **deps**: update dependency django-oscar-api-checkout to ^3.7.0
- **deps**: update dependency django-oscar to >=3.2.6,<4.1
- **deps**: update dependency pydantic to ^2.11.2

### Refactor

- migrate from poetry -> uv

## v9.2.1 (2025-04-03)

### Fix

- set correct repo urls

## v9.2.0 (2025-04-03)

### Feat

- add support for Django 5.0

### Fix

- **deps**: update dependency pydantic to ^2.11.1
- **deps**: update dependency pydantic to ^2.11.0
- **deps**: update dependency phonenumbers to ^9.0.2
- **deps**: update dependency phonenumbers to v9

### Refactor

- add pyupgrade / django-upgrade precommit hooks

## v9.1.7 (2025-03-21)

### Fix

- use NullCharField from thelabdb

## v9.1.6 (2025-03-17)

### Fix

- **deps**: update dependency thelabdb to ^0.3.0
- **deps**: update dependency xmlsec to ^1.3.15
- **deps**: update dependency django to ^4.2.20
- **deps**: update dependency cryptography to ^44.0.2

## v9.1.5 (2025-02-19)

### Fix

- make optional config actually optional
- **deps**: update dependency phonenumbers to ^8.13.55
- **deps**: update dependency cryptography to ^44.0.1
- **deps**: update dependency lxml to ^5.3.1
- **deps**: update dependency django to ^4.2.19
- **deps**: update dependency django-stubs-ext to ^5.1.3

## v9.1.4 (2025-02-05)

### Fix

- incorrect SOAP response serialization in CyberSourceReply.log_soap_response

## v9.1.3 (2025-02-03)

### Fix

- wrap order model import in TYPE_CHECKING conditional to fix overridden order models

## v9.1.2 (2025-02-03)

### Fix

- wrap order model import in TYPE_CHECKING conditional to fix overridden order models

## v9.1.1 (2025-02-03)

### Fix

- add py.typed marker
- **deps**: update dependency phonenumbers to ^8.13.54

## v9.1.0 (2025-01-30)

### Feat

- update SOAP code to use pkcs12 auth (#28272)
- add type annotations

### Fix

- typing tweaks
- **deps**: update dependency django-oscar-api-checkout to ^3.6.1

## v9.0.5 (2025-01-21)

### Fix

- ci component python version

## v9.0.4 (2025-01-21)

### Fix

- **deps**: update dependency thelabdb to ^0.2.0
- **deps**: update dependency phonenumbers to ^8.13.53
- **deps**: update dependency django to ^4.2.18
- **deps**: update dependency phonenumbers to ^8.13.52
- **deps**: update dependency django to ^4.2.17
- **deps**: update dependency phonenumbers to ^8.13.51
- **deps**: update dependency phonenumbers to ^8.13.50
- **deps**: update dependency django-oscar-api-checkout to ^3.5.1
- **deps**: update dependency phonenumbers to ^8.13.49
- **deps**: update dependency phonenumbers to ^8.13.48

## v9.0.3 (2024-10-23)

### Fix

- handle 201 reason code as a REJECT (#27811)
- **deps**: update dependency phonenumbers to ^8.13.47
- **deps**: update dependency django-oscar-api-checkout to ^3.5.0
- **deps**: update dependency phonenumbers to ^8.13.46

## v9.0.2 (2024-09-25)

### Fix

- **deps**: update dependency django-oscar to v3.2.5
- **deps**: update dependency django-oscar-api to v3.3.0
- **deps**: update dependency django-oscar to v3.2.5
- pin django-oscar version due to breaking changes in patch versions
- **deps**: update dependency phonenumbers to ^8.13.45
- **deps**: update dependency django to ^4.2.16
- **deps**: update dependency thelabdb to ^0.1.2
- **deps**: update dependency django-oscar-api-checkout to ^3.4.1

## v9.0.1 (2024-08-31)

### Fix

- **deps**: update dependency phonenumbers to ^8.13.44
- **deps**: update dependency lxml to ^5.3.0
- **deps**: update dependency phonenumbers to ^8.13.43
- **deps**: update dependency django to ^4.2.15

## v9.0.1b0 (2024-08-08)

### Fix

- **deps**: update dependency phonenumbers to ^8.13.42
- **deps**: update dependency django to ^4.2.14
- **deps**: update dependency phonenumbers to ^8.13.40
- **deps**: update dependency django to ^4.2.13
- **deps**: update dependency phonenumbers to v8.13.39
- **deps**: update dependency phonenumbers to v8.13.38
- **deps**: update dependency django-oscar-api-checkout to v3.4.0
- **deps**: update dependency python-dateutil to v2.9.0.post0
- **deps**: update dependency thelabdb to v0.1.1
- **deps**: update dependency phonenumbers to v8.13.37
- **deps**: update dependency lxml to v4.9.4
- **deps**: update dependency django-oscar to v3.2.4
- **deps**: update dependency django to v4.2.13

## v9.0.0

- Add support for capturing funds from authorization transactions.
- General refactoring and code cleanup.
- Add support for django-oscar 3.2.2
- Add support for django 4.2

## v8.2.0

- Fix Django deprecation warnings

## v8.1.1

- Fix bug in handling of Cybersource SOAP API downtime.

## v8.1.0

- Oscar 3.1 Compatibility

## v8.0.0

- Oscar 3.0 Compatibility

## v7.0.1

- Fix bug causing Bluefin to trigger payment declined signal twice per declined order.

## v7.0.0

- Support django-oscar 2.1

## v6.0.1

- Fix test suite issues by mocking Cybersource SA requests

## v6.0.0

- Remove StatsD metrics

## v5.0.0

- Add support for django-oscar 2.x.
- Drop support for django-oscar 1.x.
- Fix bug causing Transaction.reference to refer to the payment-token transaction instead of the authorization transaction.
- Fix checkout issue when using SameSite=Lax for session cookies.

## v4.0.2

- Replace a few instances of ``datetime.now`` with ``timezone.now`` to fix naive datetime warnings.

## v4.0.1

- Fix bug in Internationalization string interpolation

## v4.0.0

- Use Cybersource SOAP API for performing card authorizations
- Support Bluefin encrypted card entry / swipe devices.
- Improve Internationalization

## v3.5.0

- Make payment methods create separate ``payment.Source`` objects per Reference number (`!7 <https://gitlab.com/thelabnyc/django-oscar/django-oscar-cybersource/merge_requests/7>`_).
- Fix pate parsing bug which occurs during a spring-time daylight savings time transition.

## v3.4.1

- Fix bug with missing payment token fields on REVIEW replies.

## v3.4.0

- Adds support for ``django-oscar-api-checkout>=0.4.0``
- Fix error handling behavior in CyberSourceReplyView which often times lead to infinite loops.

## v3.3.2

- Add management command for unreadable Secure Acceptance Profiles from the database: ``python manage.py remove_unreadable_cybersource_profiles``
- Add exception try/catch into ``SecureAcceptanceProfile.get_profile`` method to more gracefully handle Fernet decryption errors thrown when fetching a profile from the database.
- Makes ``SecureAcceptanceProfile.get_profile`` method fall-back to Django settings when no readable profiles exist in the database.
- Fix unit tests broken by an expired development key

## v3.3.1

- Add ``order`` as a value for the ``CARD_REJECT_ERROR`` string template literal.

## v3.3.0

- Use Cybersource's ``reason_code`` field in addition to the ``decision`` field when deciding how to handle a response.
- Move secure acceptance profile data into the database.
    - Profiles can be configured in the Django Admin interface. A default profile is created when running migrations based on the old environment variable settings.
    - Stores the profile secret key in the using Fernet encryption via `django-fernet-fields <https://django-fernet-fields.readthedocs.io/en/latest/>`_. Therefore, you should declare a ``FERNET_KEYS`` setting in your project.
    - Since secure acceptable profiles are limited to a single domains for customer redirect pages, this change allows a single Django instance to serve multiple domains (by using multiple profiles).

## v3.2.3

- Fix Django 2.0 Deprecation warnings.

## v3.2.2

- Make it possible to use a placeholder (``{order_number}``) in ``settings.CARD_REJECT_ERROR``.

## v3.2.1

- Add better error handling to the Cybersource response view. Prevents exceptions when a customer refreshes and resends one of the payment POST requests.

## v3.2.0

- Adds an order's shipping method into calls to Cybersource. This field can then be used by decision manager to help make decision regarding order fraud.
    - Cybersource expects to receive one of the following values:
        - `sameday`: courier or same-day service
        - `oneday`: next day or overnight service
        - `twoday`: two-day service
        - `threeday`: three-day service
        - `lowcost`: lowest-cost service
        - `pickup`: store pick-up
        - `other`: other shipping method
        - `none`: no shipping method
    - You can configure the mapping of Oscar shipping method code to Cybersource shipping method codes using the ``CYBERSOURCE_SHIPPING_METHOD_DEFAULT`` and ``CYBERSOURCE_SHIPPING_METHOD_MAPPING`` Django settings.
- Added exception handling and logging for bug sometimes occurring in the Cybersource reply handler.


## v3.1.5

- Add support for Django 1.11 and Oscar 1.5

## v3.1.4

- Improve testing with tox.

## v3.1.3

- Upgrade dependencies.

## v3.1.2

- Make ``DecisionManagerNotificationView`` directly set order status instead of relying on the ``set_status`` method. This avoids issues with order status pipelines.
- Add optional ``CYBERSOURCE_DECISION_MANAGER_KEYS`` keys setting to allow token-based authentication on the decision manager web hook endpoint.
    - Default is disabled, which equates to disabled authentication.
    - To enable authentication, set it to a list of valid authentication keys/tokens.
    - When enabled, the ``DecisionManagerNotificationView`` view will inspect the ``key`` query parameter on incoming requests and compare it to the predefined keys in the setting. If it doesn't match one of the keys, the request is aborted.

## v3.1.1

- Make sure amounts sent to Cybersource are always properly quantized

## v3.1.0

- Support flagging authorizations for review with Decision Manager
    - Transactions under review are marked with status `REVIEW`.
    - Adds new boolean property to payment.Transaction model: `transaction.is_pending_review`.
    - When handling an authorization that is pending review in Decision Manager, a note is added to the order.

## v3.0.5

- Fix IntegrityError sometimes thrown when processing a declined payment.

## v3.0.4

- Fix exception from typo in record_declined_authorization.

## v3.0.3

- Fix case-mismatch of payment source types.

## v3.0.2

- Add data migration to populate `CyberSourceReply.order` on rows from before 3.0.1.

## v3.0.1

- Added foreign key from `cybersource.CyberSourceReply` from `order.Order`.

## v3.0.0

- Change to two step SOP method with discrete get_token and authorization steps. This works around a bug in Cybersource's code which will leave a pending authorization on a user's card, even if the address verification or decision manager rejects the transaction. By doing the transaction in two phases, we can catch most AVN / DM rejections before the authorization is placed on the credit card. The downside is that the client must now perform 2 separate form posts to Cybersource.

## v2.0.0

- Refactor as a plugin to django-oscar-api-checkout to eliminate code not related to Cybersource.

## v1.0.3

- Make profile, access, and secret mandatory
- Upgrade to `django-oscar-api>=1.0.4` to get rid of the need for our custom empty basket check
- Make test coverage much more expansive

## v1.0.2

- README Updates
- Added tests for FingerprintRedirectView
- Fixed a bug in the img-2 redirect url

## v1.0.1

- README Updates

## v1.0.0 (2016-01-25)

- Initial release.
