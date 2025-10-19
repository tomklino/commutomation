#!/usr/bin/env python3
import unittest
import requests
import time
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

GATEWAY_URL = "http://gateway"
GATEWAY_HTTPS_URL = "https://gateway"


class GatewayTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for _ in range(30):
            try:
                requests.get(GATEWAY_HTTPS_URL, verify=False, timeout=1)
                return
            except Exception:
                time.sleep(1)
        raise Exception("Gateway did not become ready in time")

    def test_http_redirect(self):
        response = requests.get(GATEWAY_URL + "/", allow_redirects=False)
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response.headers.get('Location', '').startswith('https://'))

    def test_api_proxy(self):
        response = requests.get(GATEWAY_HTTPS_URL + "/api/test/endpoint", verify=False)
        data = response.json()
        self.assertEqual(data.get('service'), 'mock-backend')
        self.assertEqual(data.get('path'), '/test/endpoint')

    def test_api_post(self):
        payload = {"test": "data"}
        response = requests.post(
            GATEWAY_HTTPS_URL + "/api/users",
            json=payload,
            verify=False
        )
        data = response.json()
        self.assertEqual(data.get('service'), 'mock-backend')
        self.assertEqual(data.get('method'), 'POST')
        self.assertEqual(data.get('path'), '/users')

    def test_static_files(self):
        response = requests.get(GATEWAY_HTTPS_URL + "/index.html", verify=False)
        self.assertIn("Test Static Content", response.text)

    def test_backend_headers(self):
        headers = {"X-Custom-Header": "test-value"}
        response = requests.get(
            GATEWAY_HTTPS_URL + "/api/headers",
            headers=headers,
            verify=False
        )
        data = response.json()
        response_headers = data.get('headers', {})

        self.assertIn('X-Forwarded-For', response_headers)
        self.assertTrue('X-Real-IP' in response_headers or 'X-Real-Ip' in response_headers)
        self.assertIn('X-Forwarded-Proto', response_headers)


if __name__ == '__main__':
    unittest.main(verbosity=2)
