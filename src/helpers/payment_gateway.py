import json
import requests

url = 'https://dummy-payment-server.herokuapp.com/payment'
headers = {"Content-Type": "application/json"}


def payment_gateway(user_name, payment_type, amount):
    payment_request = {"user_name": user_name, "payment_type": payment_type, "amount": amount}
    body = json.dumps(payment_request)
    response = requests.post(url=url, headers=headers, data=body)

    return response.json(), response.status_code
