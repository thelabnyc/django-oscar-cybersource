import django.dispatch

pre_build_auth_request = django.dispatch.Signal(providing_args=["extra_fields", "request", "order"])
