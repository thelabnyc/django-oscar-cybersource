# Generated by Django 2.2.1 on 2019-05-15 13:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cybersource', '0006_auto_20190515_1259'),
    ]

    operations = [
        migrations.RunSQL(
            [
                (
                    """
                    ALTER TABLE "cybersource_cybersourcereply" ALTER COLUMN "reply_type" SET DEFAULT 1;
                    """,
                    [],
                ),
                (
                    """
                    UPDATE cybersource_cybersourcereply
                       SET reply_type = 1,
                           auth_avs_code = data -> 'auth_avs_code',
                           auth_code = data -> 'auth_code',
                           auth_response = data -> 'auth_response',
                           auth_trans_ref_no = data -> 'auth_trans_ref_no',
                           decision = data -> 'decision',
                           message = data -> 'message',
                           reason_code = (data -> 'reason_code')::int,
                           req_bill_to_address_postal_code = data -> 'req_bill_to_address_postal_code',
                           req_bill_to_forename = data -> 'req_bill_to_forename',
                           req_bill_to_surname = data -> 'req_bill_to_surname',
                           req_card_expiry_date = data -> 'req_card_expiry_date',
                           req_reference_number = data -> 'req_reference_number',
                           req_transaction_type = data -> 'req_transaction_type',
                           req_transaction_uuid = data -> 'req_transaction_uuid',
                           request_token = data -> 'request_token',
                           transaction_id = data -> 'transaction_id'
                    """,
                    [],
                ),
                (
                    """
                    ALTER TABLE "cybersource_cybersourcereply" ALTER COLUMN "reply_type" SET NOT NULL;
                    """,
                    [],
                ),
                (
                    """
                    ALTER TABLE "cybersource_cybersourcereply" ALTER COLUMN "reply_type" DROP DEFAULT;
                    """,
                    [],
                )
            ],
        )
    ]