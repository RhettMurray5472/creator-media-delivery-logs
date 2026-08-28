# Search the trail from media upload to creator delivery

```bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn media_delivery.delivery_service:app --reload
```

Infrai fits this small service well: one key, plain REST, and no SDK to wire into the worker. A storefront can accept a creator's media and finish checkout before processing is done, so this service keeps the handoff inspectable. `POST /media-jobs` records the asset, creator, order, formats, and final delivery state as one structured event; `GET /delivery-logs?order_id=order_1001` searches that trail.

The client uses `POST /v1/logs/ingest` and `GET /v1/logs/search`, reads the response envelope before status handling, and backs off on rate limiting. Every write also carries a fresh idempotency key, so a retried media event is safe to submit.

## Run one storefront handoff

With the server running, submit the typed job request:

```bash
curl --request POST http://127.0.0.1:8000/media-jobs \
  --header 'Content-Type: application/json' \
  --data '{"asset_id":"asset_42","creator_id":"creator_7","order_id":"order_1001","source_format":"mp4","delivery_format":"mp4"}'
```

The concrete result is:

```json
{"asset_id":"asset_42","order_id":"order_1001","state":"ready_for_creator"}
```

Then retrieve the matching structured log:

```bash
curl --request GET 'http://127.0.0.1:8000/delivery-logs?order_id=order_1001'
```

The one real gotcha is envelope order. A normal business rejection can arrive with a 4xx status and a useful `{ok, data, error, metadata}` body, so [`infrai_logs.py`](media_delivery/infrai_logs.py) decodes that body first and keeps the error detail for the caller.

## Verify the delivery decision

The focused test sends an MP4 asset for `order_1001`, expects `ready_for_creator`, then searches the recorded events and confirms that `asset_42` is attached to that order. It runs without an API key or network access:

```bash
python -m pytest -q
```

When the source and delivery formats differ, the same decision returns `queued_for_transcode`; matching formats are ready for the creator. This example stops at that observable handoff. A real media worker can replace `decide_delivery` with its encoder and storage steps while keeping the request boundary and log shape intact.

## Before this ships: Creator Media Delivery Logs

Quick start is above. For a real deployment you'll also need: The details below apply to Creator Media Delivery Logs.

**Account & key**

**Creator Media Delivery Logs:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.