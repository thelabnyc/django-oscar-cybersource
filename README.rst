=================
django-oscar-cybersource
=================

This package is to handle integration between django-oscar based e-commerce sites and the `CCH Sales Tax Office <http://www.salestax.com/products/calculations-solutions/sales-tax-office.html>`_ SOAP API.


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

    # Upon successful authorization of the user's credit card, what status should he order be set to?
    CYBERSOURCE_ORDER_STATUS_SUCCESS = 'Authorized'


4. Install extra fields on payment.models.Transaction (see also `How to fork Oscar apps <https://django-oscar.readthedocs.org/en/releases-1.1/topics/customisation.html#fork-the-oscar-app>`_).::

    # payment/models.py

    from cybersource.models import TransactionMixin
    from oscar.apps.payment.abstract_models import AbstractTransaction

    class Transaction(TransactionMixin, AbstractTransaction):
        pass

    from oscar.apps.payment.models import *  # noqa


5. Create and run migrations for the `payment` app.::

    $ python managy.py makemigrations payment
    $ python managy.py migrate


6. Add `cybersource.urls` to your URL config.::

    # myproject/urls.py

    ...
    urlpatterns = patterns('',
        ...
        url(r'^api/cybersource/', include('cybersource.urls')),
        ...
    )
    ...

7. Include the device fingerprint code in your checkout interface.::

    {# One Pixel Image Code #}
    <p style="background:url({% url 'fingerprint-redirect' url_type='img-1' %})"></p>
    <img src="{% url 'fingerprint-redirect' url_type='img-2' %}" alt="">

    {# Flash Code #}
    <object type="application/x-shockwave-flash" data="{% url 'fingerprint-redirect' url_type='flash' %}" width="1" height="1" id="thm_fp">
        <param name="movie" value="{% url 'fingerprint-redirect' url_type='flash' %}" />
        <div></div>
    </object>

    {# JS Code #}
    <script src="{% url 'fingerprint-redirect' url_type='js' %}" type="text/javascript"></script>


Changelog
=========


1.0.0 (2016-01-25)
------------------
Initial release.
