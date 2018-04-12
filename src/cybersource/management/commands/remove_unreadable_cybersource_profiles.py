from cryptography.fernet import InvalidToken
from django.core.management.base import BaseCommand
from cybersource.models import SecureAcceptanceProfile


class Command(BaseCommand):
    help = (
        "Find all SecureAcceptanceProfile rows that can not be decrypted (using the currently configured "
        "fernet keys) and delete them from the database."
    )

    def handle(self, *args, **options):
        pks = SecureAcceptanceProfile.objects.values_list('pk', flat=True).all()
        for pk in pks:
            try:
                SecureAcceptanceProfile.objects.get(pk=pk)
            except InvalidToken:
                self.stdout.write("Removing SecureAcceptanceProfile pk={}".format(pk))
                SecureAcceptanceProfile.objects.filter(pk=pk).delete()
