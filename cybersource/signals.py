import django.dispatch

pre_build_get_token_request = django.dispatch.Signal()

pre_build_auth_request = django.dispatch.Signal()

pre_build_capture_request = django.dispatch.Signal()

received_decision_manager_update = django.dispatch.Signal()
