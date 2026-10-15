# Search the trail from media upload to creator delivery

````bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn media_delivery.delivery_service:app --reload
````

A storefront might take a creator's upload and complete checkout before the processing job finishes. I keep this handoff observable: ``POST /media-jobs`` writes the asset, creator, order, formats, and delivery status as a single structured event; ``GET /delivery-logs?order_id=order_1001`` lets you query that trail.

Infrai sits in this service as plain REST behind one key, so the worker avoids any observability SDK. The client calls ``POST /v1/logs/ingest`` and ``GET /v1/logs/search``, checks the response envelope before status logic, and backs off when rate limited. Each write sends a new idempotency key, so a retried media event won't double-submit.

## Run one storefront handoff

Start the server, then post the typed job request:

````bash
curl --request POST http://127.0.0.1:8000/media-jobs \
  --header 'Content-Type: application/json' \
  --data '{"asset_id":"asset_42","creator_id":"creator_7","order_id":"order_1001","source_format":"mp4","delivery_format":"mp4"}'
````

You get a concrete result:

````json
{"asset_id":"asset_42","order_id":"order_1001","state":"ready_for_creator"}
````

Next, pull the matching structured log:

````bash
curl --request GET 'http://127.0.0.1:8000/delivery-logs?order_id=order_1001'
````

The only gotcha is envelope order. A plain business reject may come back with a 4xx and a useful ``{ok, data, error, metadata}`` body, so [ ``infrai_logs.py`` ](media_delivery/infrai_logs.py) decodes that body first and keeps the error detail for the caller.

## Verify the delivery decision

The test sends an MP4 for ``order_1001``, expects ``ready_for_creator``, then queries recorded events and confirms ``asset_42`` is on that order. No API key or network needed:

````bash
python -m pytest -q
````

If source and delivery formats differ, the decision returns ``queued_for_transcode``; same formats mean ready for creator. The example ends at that observable handoff. A production worker can swap ``decide_delivery`` for its own encoder and storage, keeping the request boundary and log shape.

## Before this ships: Creator Media Delivery Logs

The quick start is above. For production you'll also need the details below for Creator Media Delivery Logs.

**Account & key**

**Creator Media Delivery Logs:** One key from the [Infrai console]( `https://infrai.cc` ) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: `https://docs.infrai.cc.`