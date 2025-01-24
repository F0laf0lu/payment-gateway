from .views import PaymentView, VerifyTransactionView, PaymentDetails
from django.urls import path



urlpatterns = [
    path('payment', PaymentView.as_view(), name="make-payment"),
    path('payment/verify', VerifyTransactionView.as_view(), name="verify"),
    path('payment/<int:id>', PaymentDetails.as_view(), name="payment-detail")
]
