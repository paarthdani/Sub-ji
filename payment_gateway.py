import json
import requests

url = 'https://dummy-payment-server.herokuapp.com/payment'
headers = {"Content-Type": "application/json"}


def payment_gateway(body):
    body = json.dumps(body)
    response = {}
    counter = 0

    while counter < 3:
        print(counter)
        response = requests.post(url=url, headers=headers, data=body)
        status_code = response.status_code
        if status_code == 200 and response.json().get("status") == "SUCCESS":
            break
        counter += 1
    return response.json(), response.status_code
