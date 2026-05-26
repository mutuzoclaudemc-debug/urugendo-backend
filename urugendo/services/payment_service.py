"""
Payment service integrating:
  - MTN Mobile Money (Collections API)
  - Airtel Money Rwanda
"""
import uuid
from datetime import datetime
from typing import Tuple

import httpx

from core.config import settings


# ── MTN MoMo ──────────────────────────────────────────────────────────────────

async def _mtn_get_access_token() -> str:
    """Obtain a bearer token from the MTN MoMo OAuth endpoint."""
    url = f"{settings.MTN_MOMO_BASE_URL}/collection/token/"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            auth=(settings.MTN_MOMO_API_USER, settings.MTN_MOMO_API_KEY),
            headers={
                "Ocp-Apim-Subscription-Key": settings.MTN_MOMO_SUBSCRIPTION_KEY,
            },
        )
    response.raise_for_status()
    return response.json()["access_token"]


async def mtn_request_to_pay(
    phone: str,
    amount: int,
    booking_id: int,
) -> Tuple[str, str]:
    """
    Initiate a Request-to-Pay via MTN MoMo Collections API.
    Returns (external_reference_uuid, status).
    """
    reference = str(uuid.uuid4())
    token = await _mtn_get_access_token()

    url = f"{settings.MTN_MOMO_BASE_URL}/collection/v1_0/requesttopay"
    payload = {
        "amount": str(amount),
        "currency": settings.MTN_MOMO_CURRENCY,
        "externalId": str(booking_id),
        "payer": {
            "partyIdType": "MSISDN",
            "partyId": phone.lstrip("+"),
        },
        "payerMessage": f"Urugendo ride payment – booking #{booking_id}",
        "payeeNote": f"Urugendo booking #{booking_id}",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Reference-Id": reference,
                "X-Target-Environment": settings.MTN_MOMO_ENVIRONMENT,
                "Ocp-Apim-Subscription-Key": settings.MTN_MOMO_SUBSCRIPTION_KEY,
                "X-Callback-Url": settings.MTN_MOMO_CALLBACK_URL,
                "Content-Type": "application/json",
            },
        )

    # 202 Accepted = request submitted; status checked later via webhook/polling
    if response.status_code == 202:
        return reference, "pending"

    raise ValueError(f"MTN MoMo error {response.status_code}: {response.text}")


async def mtn_check_payment_status(reference: str) -> str:
    """Poll the MTN API to get the current status of a payment."""
    token = await _mtn_get_access_token()
    url = f"{settings.MTN_MOMO_BASE_URL}/collection/v1_0/requesttopay/{reference}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Target-Environment": settings.MTN_MOMO_ENVIRONMENT,
                "Ocp-Apim-Subscription-Key": settings.MTN_MOMO_SUBSCRIPTION_KEY,
            },
        )

    response.raise_for_status()
    data = response.json()
    status_map = {
        "SUCCESSFUL": "success",
        "FAILED":     "failed",
        "PENDING":    "pending",
    }
    return status_map.get(data.get("status", "PENDING"), "pending")


# ── Airtel Money ───────────────────────────────────────────────────────────────

async def _airtel_get_access_token() -> str:
    """Obtain an OAuth token from Airtel Africa."""
    url = f"{settings.AIRTEL_BASE_URL}/auth/oauth2/token"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json={
                "client_id": settings.AIRTEL_CLIENT_ID,
                "client_secret": settings.AIRTEL_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
            headers={"Content-Type": "application/json"},
        )
    response.raise_for_status()
    return response.json()["access_token"]


async def airtel_collect(
    phone: str,
    amount: int,
    booking_id: int,
) -> Tuple[str, str]:
    """
    Initiate an Airtel Money collection (debit from customer).
    Returns (transaction_id, status).
    """
    token = await _airtel_get_access_token()
    reference = str(uuid.uuid4())

    # Airtel expects local format (no +)
    local_phone = phone.lstrip("+").lstrip("250")

    url = f"{settings.AIRTEL_BASE_URL}/merchant/v2/payments/"
    payload = {
        "reference": reference,
        "subscriber": {
            "country": "RW",
            "currency": "RWF",
            "msisdn": local_phone,
        },
        "transaction": {
            "amount": amount,
            "country": "RW",
            "currency": "RWF",
            "id": reference,
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Country": "RW",
                "X-Currency": "RWF",
            },
        )

    data = response.json()
    if data.get("status", {}).get("success"):
        transaction_id = data["data"]["transaction"]["id"]
        return transaction_id, "pending"

    raise ValueError(f"Airtel Money error: {data}")


async def airtel_check_payment_status(transaction_id: str) -> str:
    """Check the status of an Airtel Money transaction."""
    token = await _airtel_get_access_token()
    url = f"{settings.AIRTEL_BASE_URL}/standard/v1/payments/{transaction_id}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "X-Country": "RW",
                "X-Currency": "RWF",
            },
        )

    data = response.json()
    raw = data.get("data", {}).get("transaction", {}).get("status", "TS").upper()
    status_map = {
        "TS":  "success",   # Transaction Successful
        "TF":  "failed",    # Transaction Failed
        "TP":  "pending",   # Transaction Pending
        "TIP": "pending",   # Transaction In Progress
    }
    return status_map.get(raw, "pending")
