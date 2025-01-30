# Create the .po and .mo files used for i18n
.PHONY: translations
translations:
	cd src/cybersource && \
	django-admin makemessages -a && \
	django-admin compilemessages

.PHONY: system_deps
system_deps:
	apt-get update && \
    apt-get install -y \
        gettext \
        libxml2-dev \
        libxmlsec1-dev \
        libxmlsec1-openssl \
        pkg-config
