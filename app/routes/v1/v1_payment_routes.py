# routes/payment.py

from app.auth import get_current_user
from app.routes.v1.v1_autoPay_routes import get_or_create_wallet
import razorpay
import os
import uuid
from fastapi import APIRouter, HTTPException,Request, Depends
from pydantic import BaseModel
from ...models import Transaction

router = APIRouter(prefix="/payment", tags=["Payment"])

client = razorpay.Client(auth=(
    "rzp_test_SNylmVYadLGmJy",
    "GiHFyzHTxjq7J1s7rkOUMneJ"
))


class CreateOrderRequest(BaseModel):
    user_id: str
    amount: float


@router.post("/create-order")
def create_order(data: CreateOrderRequest):

    try:

        order = client.order.create({
            "amount": int(data.amount * 100),
            "currency": "INR",
            "payment_capture": 1
        })

        tx = Transaction(
            tx_id=str(uuid.uuid4()),
            razorpay_order_id=order["id"],
            user_id=data.user_id,
            amount=data.amount,
            status="APPROVED"  # We will update to SUCCESS/FAILED in webhook
        )


        tx.save()
        wallet = get_or_create_wallet(tx.user_id)
        wallet.update(inc__balance=data.amount)

        
        return {
            "order_id": order["id"],
            "key": "rzp_test_SNylmVYadLGmJy",
            "amount": order["amount"]
        }

    except Exception as e:

        print("RAZORPAY ERROR:", e)

        raise HTTPException(status_code=400, detail=str(e))
import hmac
import hashlib
import json
from datetime import datetime

@router.post("/razorpay-webhook")
async def razorpay_webhook(request: Request):

    body = await request.body()
    received_signature = request.headers.get("X-Razorpay-Signature")

    generated_signature = hmac.new(
        bytes(os.getenv("RAZORPAY_WEBHOOK_SECRET"), 'utf-8'),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(generated_signature, received_signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    payload = json.loads(body)
    event = payload.get("event")

    if event == "payment.captured":

        payment_entity = payload["payload"]["payment"]["entity"]
        order_id = payment_entity["order_id"]
        payment_id = payment_entity["id"]

        transaction = Transaction.objects(
            razorpay_order_id=order_id
        ).first()

        if transaction:

            # 🔁 Prevent duplicate processing
            if transaction.status == "SUCCESS":
                return {"status": "already processed"}

            transaction.status = "SUCCESS"
            transaction.razorpay_payment_id = payment_id
            transaction.confirmed_at = datetime.utcnow()
            transaction.save()

            # 🔥 YAHAN BID CONFIRM KARO
            # Bid.objects(id=transaction.bid_id).update(set__status="CONFIRMED")

    elif event == "payment.failed":

        payment_entity = payload["payload"]["payment"]["entity"]
        order_id = payment_entity["order_id"]

        transaction = Transaction.objects(
            razorpay_order_id=order_id
        ).first()

        if transaction:
            transaction.status = "FAILED"
            transaction.save()

    return {"status": "ok"}