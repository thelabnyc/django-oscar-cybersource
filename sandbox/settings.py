from django.utils.translation import gettext_lazy as _
from oscar.defaults import *  # noqa
from psycopg2cffi import compat
import os

compat.register()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEBUG = True
SECRET_KEY = 'li0$-gnv)76g$yf7p@(cg-^_q7j6df5cx$o-gsef5hd68phj!4'
SITE_ID = 1

USE_I18N = True
LANGUAGE_CODE = 'en-us'
LANGUAGES = (
    ('en-us', _('English')),
    ('es', _('Spanish')),
)

ROOT_URLCONF = 'urls'
ALLOWED_HOSTS = ['*']

# Used to encrypt secure acceptance profiles in the database
FERNET_KEYS = [
    'epM8Bk2YJlLVLsHqUlriW0Ma7rDpPfHMrAhmxmwdbVqqdgPNEqzeYYxheLdKLPe',
]

INSTALLED_APPS = [
    # Core Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.postgres',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.flatpages',

    # django-oscar
    'oscar',
    'oscar.apps.analytics',
    'oscar.apps.checkout',
    'oscar.apps.address',
    'oscar.apps.shipping',
    'oscar.apps.catalogue',
    'oscar.apps.catalogue.reviews',
    'oscar.apps.partner',
    'oscar.apps.basket',
    'payment',  # 'oscar.apps.payment',
    'oscar.apps.offer',
    'order',  # 'oscar.apps.order',
    'oscar.apps.customer',
    'oscar.apps.search',
    'oscar.apps.voucher',
    'oscar.apps.wishlists',
    'oscar.apps.dashboard',
    'oscar.apps.dashboard.reports',
    'oscar.apps.dashboard.users',
    'oscar.apps.dashboard.orders',
    'oscar.apps.dashboard.catalogue',
    'oscar.apps.dashboard.offers',
    'oscar.apps.dashboard.partners',
    'oscar.apps.dashboard.pages',
    'oscar.apps.dashboard.ranges',
    'oscar.apps.dashboard.reviews',
    'oscar.apps.dashboard.vouchers',
    'oscar.apps.dashboard.communications',
    'oscar.apps.dashboard.shipping',

    # 3rd-party apps that oscar depends on
    'widget_tweaks',
    'haystack',
    'treebeard',
    'sorl.thumbnail',
    'django_tables2',

    # django-oscar-api
    'rest_framework',
    'oscarapi',

    'oscarapicheckout',
    'cybersource',
]

MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'oscar.apps.basket.middleware.BasketMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'oscar.apps.search.context_processors.search_form',
                'oscar.apps.checkout.context_processors.checkout',
                'oscar.apps.customer.notifications.context_processors.notifications',
                'oscar.core.context_processors.metadata',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': 'postgres',
        'PORT': 5432,
    }
}

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'cybersource-testing-sandbox',
    }
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'public', 'static')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'public', 'media')

# Order Status Pipeline
# Needed by oscarapicheckout
ORDER_STATUS_PENDING = 'Pending'
ORDER_STATUS_PAYMENT_DECLINED = 'Payment Declined'
ORDER_STATUS_AUTHORIZED = 'Authorized'

# Other statuses
ORDER_STATUS_SHIPPED = 'Shipped'
ORDER_STATUS_CANCELED = 'Canceled'

OSCAR_INITIAL_ORDER_STATUS = ORDER_STATUS_PENDING
OSCARAPI_INITIAL_ORDER_STATUS = ORDER_STATUS_PENDING
OSCAR_ORDER_STATUS_PIPELINE = {
    ORDER_STATUS_PENDING: (ORDER_STATUS_PAYMENT_DECLINED, ORDER_STATUS_AUTHORIZED, ORDER_STATUS_CANCELED),
    ORDER_STATUS_PAYMENT_DECLINED: (ORDER_STATUS_CANCELED, ),
    ORDER_STATUS_AUTHORIZED: (ORDER_STATUS_SHIPPED, ORDER_STATUS_CANCELED, ORDER_STATUS_PAYMENT_DECLINED),
    ORDER_STATUS_SHIPPED: (),
    ORDER_STATUS_CANCELED: (),
}

OSCAR_INITIAL_LINE_STATUS = ORDER_STATUS_PENDING
OSCAR_LINE_STATUS_PIPELINE = {
    ORDER_STATUS_PENDING: (ORDER_STATUS_SHIPPED, ORDER_STATUS_CANCELED),
    ORDER_STATUS_SHIPPED: (),
    ORDER_STATUS_CANCELED: (),
}

OSCAR_ALLOW_ANON_CHECKOUT = True
OSCAR_DEFAULT_CURRENCY = 'USD'
OSCARAPI_BLOCK_ADMIN_API_ACCESS = False

# Cybersource Config
CYBERSOURCE_ORG_ID = 'someorg'
CYBERSOURCE_PROFILE = '2A37F989-C8B2-4FEF-ACCF-2562577780E2'
CYBERSOURCE_ACCESS = '62a67633d0063c26a9c578bd9dcab18d'
CYBERSOURCE_SECRET = (
    'fbd10ee555984a5eb1354aefc75006666b9a084ee328481fadd14737fed5d34e'
    'fe2d8888c474460796fcaaa3fc1d5694382273dffd3548b0918c41534bb8a5b8'
    '043fe54427eb41b1a6e00245db7eb86fd7c5378bedf54a9c95c6d62b14cf66e5'
    'e80a775c32d44a19b09531be1ee5c76fb817273ad12c4613a3744e9a57bce0a1'
)
CYBERSOURCE_REDIRECT_PENDING = 'checkout:index'
CYBERSOURCE_REDIRECT_SUCCESS = 'checkout:thank-you'
CYBERSOURCE_REDIRECT_FAIL = 'checkout:index'

# Cybersource SOAP Config
CYBERSOURCE_MERCHANT_ID = os.environ.get('CYBERSOURCE_MERCHANT_ID')
CYBERSOURCE_SOAP_KEY = os.environ.get('CYBERSOURCE_SOAP_KEY')

# Configure payment methods
API_ENABLED_PAYMENT_METHODS = [
    {
        'method': 'cybersource.methods.Cybersource',
        'permission': 'oscarapicheckout.permissions.Public',
    },
    {
        'method': 'cybersource.methods.Bluefin',
        'permission': 'oscarapicheckout.permissions.Public',
    },
]

CYBERSOURCE_SHIPPING_METHOD_MAPPING = {
    'free-shipping': 'lowcost',
    'ups-ground': 'threeday',
    'ups-2-day': 'twoday',
    'ups-next-day': 'oneday',
}
