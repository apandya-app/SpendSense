import os
from apify_client import ApifyClient

def analyse_receipt(receipt_url):
    client = ApifyClient(
        os.environ["APIFY_API_TOKEN"]
    )

    run = client.actor(
        "litezero/receipt-invoice-ocr-parser"
    ).call(
        run_input={"receiptUrl": receipt_url}
    )

    if run is None:
        raise RuntimeError("Receipt analysis failed")

    results = list(
        client.dataset(
            run.default_dataset_id
        ).iterate_items()
    )

    if not results:
        raise ValueError("No receipt data returned")

    receipt = results[0]

    merchant = receipt.get("vendor") or {}
    if isinstance(merchant, dict):
        merchant = merchant.get("name", "Unknown")

    amount = receipt.get("total")
    if amount is None:
        raise ValueError("Receipt total was not detected")

    return {
        "merchant": merchant,
        "amount": float(amount),
        "date": receipt.get("date"),
        "currency": receipt.get("currency"),
        "category": "Other",
    }
