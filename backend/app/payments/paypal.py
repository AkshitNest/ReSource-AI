import base64
import os
import requests


class PayPalConfigurationError(RuntimeError):
    pass


class PayPalClient:
    def __init__(self):
        self.client_id = os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        self.base_url = os.getenv("PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com")

    @property
    def configured(self):
        return bool(self.client_id and self.client_secret)

    def _token(self):
        if not self.client_id or not self.client_secret:
            raise PayPalConfigurationError("PayPal Sandbox credentials are not configured")
        encoded = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        response = requests.post(f"{self.base_url}/v1/oauth2/token", headers={"Authorization": f"Basic {encoded}", "Content-Type": "application/x-www-form-urlencoded"}, data={"grant_type": "client_credentials"}, timeout=15)
        response.raise_for_status()
        return response.json()["access_token"]

    def create_order(self, amount, currency="INR", reference="resource-packet"):
        token = self._token()
        response = requests.post(f"{self.base_url}/v2/checkout/orders", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "PayPal-Request-Id": reference}, json={"intent": "CAPTURE", "purchase_units": [{"reference_id": reference, "amount": {"currency_code": currency, "value": f"{amount:.2f}"}}]}, timeout=15)
        response.raise_for_status()
        return response.json()

    def capture_order(self, order_id):
        token = self._token()
        response = requests.post(f"{self.base_url}/v2/checkout/orders/{order_id}/capture", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=15)
        response.raise_for_status()
        return response.json()
