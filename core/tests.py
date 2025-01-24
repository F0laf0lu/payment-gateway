from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from .models import Payment


class PaymentTests(APITestCase):
    def test_payment_initialization(self):
        data = {"name": "John Doe", "email": "john@example.com", "amount": "5000"}
        response = self.client.post("/api/v1/payment", data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("authorization_url", response.data)


class PaymentDetailsTestCase(APITestCase):

    def setUp(self):
        """Set up test data before each test."""
        self.payment = Payment.objects.create(
            name="John Doe",
            email="john@example.com",
            amount=100.50,
            status="completed",
        )
        self.valid_url = reverse("payment-detail", kwargs={"id": self.payment.id})
        self.invalid_url = reverse("payment-detail", kwargs={"id": 999})

    def test_get_payment_success(self):
        """Test retrieving payment details successfully."""
        response = self.client.get(self.valid_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["payment"]["id"], self.payment.id)
        self.assertEqual(response.data["payment"]["customer_name"], "John Doe")

    def test_get_payment_not_found(self):
        """Test retrieving non-existing payment."""
        response = self.client.get(self.invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["status"], "error")
        self.assertEqual(response.data["message"], "Payment not found.")
