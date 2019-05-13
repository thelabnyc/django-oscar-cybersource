.. _installation:

Installation
============


Caveats
-------

1. Requires and `django-oscar>=1.5` and `django-oscar-api>=1.3`.
2. Your project must use PostgreSQL, since cybersource.models.CyberSourceReply uses an HStore field to log request data.
3. You must fork the Oscar payment app to add a mixin to the transaction model.


Install
-------


Install the `django-oscar-cybersource` packages.

.. code-block:: python

    $ pip install git+https://gitlab.com/thelabnyc/django-oscar-cybersource.git#r1.0.0

Add `cybersource` to your `INSTALLED_APPS`

.. code-block:: python

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

Add some attributes to `settings.py` to configure how the application should connect to Cybersource.

.. code-block:: python

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

    # Enter the mapping from project specific shipping methods code to Cybersource expected names. Valid Cybersource values are:
    # - "sameday": courier or same-day service
    # - "oneday": next day or overnight service
    # - "twoday": two-day service
    # - "threeday": three-day service
    # - "lowcost": lowest-cost service
    # - "pickup": store pick-up
    # - "other": other shipping method
    # - "none": no shipping method
    CYBERSOURCE_SHIPPING_METHOD_DEFAULT = 'none'
    CYBERSOURCE_SHIPPING_METHOD_MAPPING = {
        'free-shipping': 'lowcost',
        'ups-ground': 'threeday',
        'ups-2-day': 'twoday'
        'ups-next-day': 'oneday',
    }


Install extra fields on payment.models.Transaction (see also `How to fork Oscar apps <https://django-oscar.readthedocs.org/en/releases-1.1/topics/customisation.html#fork-the-oscar-app>`_).

.. code-block:: python

    # payment/models.py

    from cybersource.models import TransactionMixin
    from oscar.apps.payment.abstract_models import AbstractTransaction

    class Transaction(TransactionMixin, AbstractTransaction):
        pass

    from oscar.apps.payment.models import *  # noqa


Create and run migrations for the `payment` app.

.. code-block:: python

    $ python manage.py makemigrations payment
    $ python manage.py migrate


Add `cybersource.urls` to your URL config.

.. code-block:: python

    # myproject/urls.py
    from cybersource.app import application as cybersource

    ...
    urlpatterns = patterns('',
        ...
        url(r'^api/cybersource/', include(cybersource.urls)),
        ...
    )
    ...

In the Cybersource Secure Acceptance dashboard, set the customer response page to https://www.my-host.com/api/cybersource/cybersource-reply/. If using Decision Manager, set its notification URL to https://www.my-host.com/api/cybersource/decision-manager-review-notification/.

Finally, include the device fingerprint code in your checkout interface.

.. code-block:: python

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
