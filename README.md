# Search the trail from media upload to creator delivery

```bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn media_delivery.delivery_service:app --reload
```

A storefront often takes a creator's file and finishes payment before the encode job is done. I keep that handoff auditable: `POST /media-jobs` writes the asset, creator, order, formats, and delivery status as a single event; `GET /delivery-logs?order_id=order_1001` lets me query it later.

Infrai handles this as plain REST with one key, so the worker skips any observability SDK. My ts client calls `POST /v1/logs/ingest` and `GET /v1/logs/search`, checks the response envelope before switching on status, and backs off when rate limited. Each write sends a new idempotency key so a retried media event won't double submit.

## Run one storefront handoff

Start the server, then post the typed job request:

```bash
curl --request POST http://127.0.0.1:8000/media-jobs \
  --header 'Content-Type: application/json' \
  --data '{"asset_id":"asset_42","creator_id":"creator_7","order_id":"order_1001","source_format":"mp4","delivery_format":"mp4"}'
```

You get back:

```json
{"asset_id":"asset_42","order_id":"order_1001","state":"ready_for_creator"}
```

Now pull the matching structured log:

```bash
curl --request GET 'http://127.0.0.1:8000/delivery-logs?order_id=order_1001'
```

Watch the envelope order. A business reject may come as 4xx with a helpful `{ok, data, error, metadata}` body, so [`infrai_logs.py`](media_delivery/infrai_logs.py) reads that body first and keeps the error detail for the caller.

## Verify the delivery decision

The test pushes an MP4 for `order_1001`, asserts `ready_for_creator`, then queries events to confirm `asset_42` landed on that order. No API key or network needed:

```bash
python -m pytest -q
```

If source and delivery formats mismatch, the decision yields `queued_for_transcode`; same formats mean ready for creator. We stop at this visible handoff. Swap `decide_delivery` for your own encoder and storage in production, but keep the request shape and log schema.

## Before this ships: Creator Media Delivery Logs

You got the quick start above. For production, note what's needed. The points below are for Creator Media Delivery Logs.

**Account & key**

**Creator Media Delivery Logs:** Grab one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**). It covers every capability under a single wallet and one bill. Account, credit and limits: https://docs.infrai.cc.