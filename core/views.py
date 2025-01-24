from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
import requests
from .models import Payment
import logging
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ObjectDoesNotExist


logger = logging.getLogger(__name__)

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
PAYSTACK_INITIALIZE_URL = "https://api.paystack.co/transaction/initialize"
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/"


class PaymentView(APIView):
    def post(self, request, *args, **kwargs):
        name = request.data.get("name")
        email = request.data.get("email")
        amount = request.data.get("amount")

        logger.debug("Payment initiated for email: %s, name: %s, amount: %s", email, name, amount)

        if not name or not email or not amount:
            return Response(
                {"error": "Name, email, and amount are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount_in_kobo = int(amount) * 100
        except ValueError:
            return Response(
                {"error": "Invalid amount format."}, status=status.HTTP_400_BAD_REQUEST
            )

        payment_data = {
            "email": email,
            "amount": amount_in_kobo,
            "currency": "NGN",
            "callback_url": "http://127.0.0.1:8000/api/v1/payment/verify",
        }

        try:
            response = requests.post(
                "https://api.paystack.co/transaction/initialize",
                json=payment_data,
                headers={
                    "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )

            if response.status_code == 200:
                payment_info = response.json()
                transaction_id = payment_info["data"]["reference"]

                logger.debug(f"Transaction initialized: {transaction_id}")

                Payment.objects.create(
                    name=name,
                    email=email,
                    amount=amount,
                    currency="NGN",
                    status="pending",
                    transaction_id=transaction_id,
                )

                return Response(payment_info["data"], status=status.HTTP_200_OK)

            return Response(response.json(), status=response.status_code)

        except requests.exceptions.RequestException as e:
            return Response(
                {"error": "Payment service is unavailable. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


@method_decorator(csrf_protect, name="dispatch")
class VerifyTransactionView(APIView):
    def get(self, request):
        reference = request.query_params.get("reference")

        if not reference:
            return Response(
                {"error": "Transaction reference is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        response = requests.get(f"{PAYSTACK_VERIFY_URL}{reference}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data["data"]["status"] == "success":
                payment = Payment.objects.get(transaction_id=reference)
                payment.status = "success"
                payment.save()

                return Response(
                    {   
                        "status": "success",
                        "message": "Transaction verified successfully",
                        "data": {
                            "id": payment.id,
                            "payment_status": payment.status,
                            "amount": payment.amount,
                            "currency":data["data"]["currency"],
                            "channel": data["data"]["channel"],
                            "paid_at" : payment.updated_at,                        
                        },
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                payment = Payment.objects.get(transaction_id=reference)
                payment.status = "failed"
                payment.save()
                return self.error_response("Transaction not successful", status.HTTP_400_BAD_REQUEST)

        return Response(response.json(), status=response.status_code)


class PaymentDetails(APIView):

    def get(self, request, *args, **kwargs):
        payment_id = kwargs.get("id")
        if not payment_id:
            return Response(
                {"status": "error", "message": "Payment ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = Payment.objects.get(pk=payment_id)
            payment_data = {
                "id": payment.id,
                "customer_name": payment.name,
                "customer_email": payment.email,
                "amount": payment.amount,
                "status": payment.status,
            }
            return Response(
                {
                    "payment": payment_data,
                    "status": "success",
                    "message": "Payment details retrieved successfully.",
                },
                status=status.HTTP_200_OK,
            )
        except ObjectDoesNotExist:
            return Response(
                {"status": "error", "message": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"status": "error", "message": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
