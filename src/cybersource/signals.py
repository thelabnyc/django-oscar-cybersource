import django.dispatch

pre_build_get_token_request = django.dispatch.Signal(providing_args=["extra_fields", "request", "order", "method_key"])
pre_build_auth_request = django.dispatch.Signal(providing_args=["extra_fields", "request", "order", "token", "method_key"])
received_decision_manager_update = django.dispatch.Signal(providing_args=["order", "transaction", "update"])
