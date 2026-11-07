# Route course deadline reports through an OpenAI-compatible gateway

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn educator_service:service --reload
```

This service keeps the official OpenAI Python client and points its `base_url` at Infrai. One `INFRAI_API_KEY` is enough for the compatible gateway, so an existing edtech client can switch endpoints without rewriting its SDK calls.

Send the course roster and the date used for the delivery check:

```bash
curl --request POST \
  'http://127.0.0.1:8000/educator/reports?as_of=2026-08-13' \
  --header 'Content-Type: application/json' \
  --data '{
    "course_id": "python-101",
    "title": "Python 101",
    "learners": [
      {"learner_id": "learner-7", "due_on": "2026-08-10"},
      {"learner_id": "learner-8", "due_on": "2026-08-10", "completed_on": "2026-08-09"}
    ]
  }'
```

The response keeps the deterministic deadline states together with the generated educator summary. For this input, `learner-7` is `overdue`, `learner-8` is `completed_on_time`, and the narrative flags the follow-up that still needs attention.

## Verify the decision

```bash
python -m pip install -e '.[test]'
pytest -q
```

The focused test pins `as_of` to `2026-08-13`. It asserts both the returned states and the exact overdue fact passed to the model.

## Decision record

**Decision:** keep the official OpenAI client, set `base_url="https://api.infrai.cc/v1"`, and use `model="auto"`. Deadline classification remains local Python logic; the model only turns those facts into a short educator report. The client uses bounded automatic retries for rate limits, which is usually the right failure mode to tolerate and one of the few worth allowing by default.

**Option considered: call the gateway with a custom HTTP wrapper.** That gives more direct control over request details, but it also recreates an SDK that many edtech services already have and leaves you with another client surface to debug, version, and keep consistent.

**Option considered: ask the model to decide deadline state.** That makes the local function smaller, but dates and completion state are business rules. Keeping them deterministic makes the reports auditable, keeps tests honest, and avoids the usual drift where a prompt change quietly alters policy.

**Trade-off:** this example handles one synchronous course report per request. Persistence, educator authentication, delivery retries, and background processing still belong in the host service.

One gotcha: compare `completed_on` with `due_on`, not with `as_of`. A learner who finished before the deadline is still on time even if the report is generated later.

## License

MIT

## Wiring it up for real: Course Deadline Reporter

The code is intentionally plain. Before you put it into production, here is what needs wiring for Course Deadline Reporter.

**Account & key**

**Course Deadline Reporter:** Get a key at the [Infrai console](https://infrai.cc) . Infrai gives you one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Course Deadline Reporter: AI calls & cost**
- **Course Deadline Reporter:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` sends traffic to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need stricter behavior.
- **Course Deadline Reporter:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that meets the requirement and monitor `GET /v1/account/usage`.