from mcp.server.fastmcp import FastMCP

from .client import LocalStripeClient
from .config import Settings
from .errors import StripeAPIError

VALID_REASONS = ("duplicate", "fraudulent", "requested_by_customer")

settings = Settings.from_env()
client = LocalStripeClient(settings.base_url, settings.api_key)
mcp = FastMCP(
    "localstripe-refund-agent",
    host=settings.host,
    port=settings.port,
)


@mcp.tool()
async def lookup_charge(charge_id: str) -> dict:
    """Retrieve a Stripe charge by id (ch_…).

    Use before issuing a refund to verify amount, currency, status,
    amount_refunded, and the `refunded` flag.
    """
    try:
        return await client.get(f"/v1/charges/{charge_id}")
    except StripeAPIError as e:
        raise RuntimeError(str(e))


@mcp.tool()
async def lookup_payment_intent(pi_id: str) -> dict:
    """Retrieve a PaymentIntent by id (pi_…).

    Its `latest_charge` is the charge that would be refunded.
    """
    try:
        return await client.get(f"/v1/payment_intents/{pi_id}")
    except StripeAPIError as e:
        raise RuntimeError(str(e))


@mcp.tool()
async def list_recent_charges(
    customer: str | None = None,
    email: str | None = None,
    limit: int = 10,
) -> dict:
    """List recent charges, optionally filtered by customer id or email.

    If `email` is given and `customer` is not, the first customer matching
    that email is looked up and used as the filter. Returns
    {"data": []} when no customer matches. `limit` is capped at 100.
    """
    limit = max(1, min(int(limit), 100))
    try:
        if customer is None and email is not None:
            customers = await client.get(
                "/v1/customers", params={"email": email, "limit": 1}
            )
            data = customers.get("data") or []
            if not data:
                return {"data": []}
            customer = data[0]["id"]
        params: dict = {"limit": limit}
        if customer is not None:
            params["customer"] = customer
        return await client.get("/v1/charges", params=params)
    except StripeAPIError as e:
        raise RuntimeError(str(e))


@mcp.tool()
async def list_refunds_for_charge(charge_id: str) -> dict:
    """List refunds already issued against a charge.

    Use before create_refund to avoid duplicate refunds and to see
    any prior `metadata.reason` / `metadata.reason_detail` audit fields.
    """
    try:
        return await client.get("/v1/refunds", params={"charge": charge_id})
    except StripeAPIError as e:
        raise RuntimeError(str(e))


@mcp.tool()
async def create_refund(
    charge_or_pi: str,
    reason: str,
    amount: int | None = None,
    reason_detail: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Refund a charge (ch_…) or a PaymentIntent's latest charge (pi_…).

    Required:
      - charge_or_pi: must start with `ch_` or `pi_`.
      - reason: one of `duplicate`, `fraudulent`, `requested_by_customer`.

    Optional:
      - amount: positive integer in minor units (e.g. cents). Omit for a
        full refund of the remaining refundable amount.
      - reason_detail: free-text justification. Stored in `metadata.reason_detail`.
      - dry_run: when True, validates and returns a preview WITHOUT issuing
        the refund. The preview includes `amount`, `currency`, and
        `remaining_refundable_after` so the agent can confirm intent before
        re-calling with dry_run=False.
    """
    if reason not in VALID_REASONS:
        raise ValueError(f"reason must be one of {list(VALID_REASONS)}")
    if amount is not None and (not isinstance(amount, int) or amount <= 0):
        raise ValueError("amount must be a positive integer (minor units)")
    if not (charge_or_pi.startswith("ch_") or charge_or_pi.startswith("pi_")):
        raise ValueError("charge_or_pi must start with ch_ or pi_")

    try:
        if charge_or_pi.startswith("pi_"):
            pi = await client.get(f"/v1/payment_intents/{charge_or_pi}")
            charge_id = pi.get("latest_charge")
            if not charge_id:
                raise ValueError("PaymentIntent has no charge to refund")
        else:
            charge_id = charge_or_pi

        charge = await client.get(f"/v1/charges/{charge_id}")
    except StripeAPIError as e:
        raise RuntimeError(str(e))

    if charge.get("status") == "failed":
        raise ValueError("Cannot refund a failed payment.")
    if charge.get("refunded"):
        raise ValueError("Charge is already fully refunded.")

    remaining = charge["amount"] - charge.get("amount_refunded", 0)
    refund_amount = amount if amount is not None else remaining
    if refund_amount > remaining:
        raise ValueError(
            f"amount {refund_amount} exceeds remaining refundable {remaining}"
        )

    preview = {
        "dry_run": True,
        "charge": charge["id"],
        "currency": charge["currency"],
        "amount": refund_amount,
        "remaining_refundable_before": remaining,
        "remaining_refundable_after": remaining - refund_amount,
        "reason": reason,
        "reason_detail": reason_detail,
        "would_fully_refund": (remaining - refund_amount) == 0,
    }
    if dry_run:
        return preview

    # localstripe's Refund.__init__ rejects unknown kwargs (resources.py:2675-2676),
    # so `reason` lives in metadata only — never as a top-level form field.
    form: dict = {"charge": charge["id"]}
    if amount is not None:
        form["amount"] = amount
    metadata = {"reason": reason}
    if reason_detail is not None:
        metadata["reason_detail"] = reason_detail
    form["metadata"] = metadata

    try:
        return await client.post("/v1/refunds", form)
    except StripeAPIError as e:
        raise RuntimeError(str(e))


def main() -> None:
    mcp.run(transport=settings.transport)
