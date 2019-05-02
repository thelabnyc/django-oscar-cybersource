CHECKOUT_ORDER_ID = 'checkout_order_id'
CHECKOUT_FINGERPRINT_SESSION_ID = 'cybersource_fingerprint_session_id'

# Default code for the email to send after successful checkout
DECISION_ACCEPT = 'ACCEPT'
DECISION_REVIEW = 'REVIEW'
DECISION_DECLINE = 'DECLINE'
DECISION_ERROR = 'ERROR'

TERMINAL_DESCRIPTOR = 'Ymx1ZWZpbg=='

# noqa: E501
CYBERSOURCE_RESPONSES = {
    '100': 'Successful transaction.',
    '101': 'The request is missing one or more required fields.',
    '102': 'One or more fields in the request contains invalid data.',
    '104': 'The merchantReferenceCode sent with this authorization request matches the merchantReferenceCode of another authorization request that you sent in the last 15 minutes.',
    '150': 'Error: General system failure. ',
    '151': 'Error: The request was received but there was a server timeout. This error does not include timeouts between the client and the server.',
    '152': 'Error: The request was received, but a service did not finish running in time.',
    '201': 'The issuing bank has questions about the request. You do not receive an authorization code in the reply message, but you might receive one verbally by calling the processor.',
    '202': 'Expired card. You might also receive this if the expiration date you provided does not match the date the issuing bank has on file.',
    '203': 'General decline of the card. No other information provided by the issuing bank.',
    '204': 'Insufficient funds in the account.',
    '205': 'Stolen or lost card.',
    '207': 'Issuing bank unavailable.',
    '208': 'Inactive card or card not authorized for card-not-present transactions.',
    '210': 'The card has reached the credit limit. ',
    '211': 'Invalid card verification number.',
    '221': 'The customer matched an entry on the processor\'s negative file.',
    '231': 'Invalid account number.',
    '232': 'The card type is not accepted by the payment processor.',
    '233': 'General decline by the processor.',
    '234': 'There is a problem with your CyberSource merchant configuration.',
    '235': 'The requested amount exceeds the originally authorized amount. Occurs, for example, if you try to capture an amount larger than the original authorization amount. This reason code only applies if you are processing a capture through the API.',
    '236': 'Processor Failure',
    '238': 'The authorization has already been captured. This reason code only applies if you are processing a capture through the API.',
    '239': 'The requested transaction amount must match the previous transaction amount. This reason code only applies if you are processing a capture or credit through the API.',
    '240': 'The card type sent is invalid or does not correlate with the credit card number.',
    '241': 'The request ID is invalid. This reason code only applies when you are processing a capture or credit through the API.',
    '242': 'You requested a capture through the API, but there is no corresponding, unused authorization record. Occurs if there was not a previously successful authorization request or if the previously successful authorization has already been used by another capture request. This reason code only applies when you are processing a capture through the API.',
    '243': 'The transaction has already been settled or reversed.',
    '246': 'The capture or credit is not voidable because the capture or credit information has already been submitted to your processor. Or, you requested a void for a type of transaction that cannot be voided. This reason code applies only if you are processing a void through the API.',
    '247': 'You requested a credit for a capture that was previously voided. This reason code applies only if you are processing a void through the API.',
    '250': 'Error: The request was received, but there was a timeout at the payment processor.',
    '520': 'The authorization request was approved by the issuing bank but declined by CyberSource based on your Smart Authorization settings.',
}
