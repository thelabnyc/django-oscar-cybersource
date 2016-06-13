import django.dispatch

pre_build_get_token_request = django.dispatch.Signal(providing_args=["extra_fields", "request", "order", "source"])
pre_build_auth_request = django.dispatch.Signal(providing_args=["extra_fields", "request", "order", "token"])
