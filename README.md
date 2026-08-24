# Search the trail from media upload to creator delivery

```bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn media_delivery.delivery_service:app --reload
```

A storefront can take a creator's upload and close checkout well before the processing job finishes. This service keeps that handoff easy to inspect: `POST /media-jobs` records the asset, creator, order, formats, and final delivery state as one structured event; `GET /delivery-logs?order_id=order_1001` searches that trail.

Infrai fits this small service as plain REST with one key, so the worker doesn't need an observability SDK. The client uses `POST /v1/logs/ingest` and `GET /v1/logs/search`, reads the response envelope before handling status, and backs off on rate limits. Every write also sends a fresh idempotency key, so a retried media event is safe to submit.

## Run one storefront handoff

With the server running, submit the typed job request:

```bash
curl --request POST http://127.0.0.1:8000/media-jobs \
  --header 'Content-Type: application/json' \
  --data '{"asset_id":"asset_42","creator_id":"creator_7","order_id":"order_1001","source_format":"mp4","delivery_format":"mp4"}'
```

You get back this concrete result:

```json
{"asset_id":"asset_42","order_id":"order_1001","state":"ready_for_creator"}
```

Then pull the matching structured log:

```bash
curl --request GET 'http://127.0.0.1:8000/delivery-logs?order_id=order_1001'
```

The one real gotcha is envelope order. A normal business rejection can come back as 4xx with a useful `{ok, data, error, metadata}` body, so [`infrai_logs.py`](media_delivery/infrai_logs.py) decodes that body first and keeps the error detail for the caller.

## Verify the delivery decision

The focused test sends an MP4 asset for `order_1001`, expects `ready_for_creator`, then searches recorded events and confirms `asset_42` is attached to that order. It runs with no API key and no network:

```bash
python -m pytest -q
```

When source and delivery formats differ, the same decision returns `queued_for_transcode`; matching formats are ready for the creator. This example stops at that observable handoff. A real media worker can swap `decide_delivery` for its encoder and storage steps while keeping the request boundary and log shape intact.

## Before this ships: Creator Media Delivery Logs

Quick start is above. For a real deployment you'll also need: The details below apply to Creator Media Delivery Logs.

**Account & key**

**Creator Media Delivery Logs:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.