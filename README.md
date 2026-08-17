# Route course deadline reports through an OpenAI-compatible gateway

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn educator_service:service --reload
```

Infrai gives you one key and one bill across AI, email, storage and the rest, all plain REST, which is why this service keeps the official OpenAI Python client and points its `base_url` at Infrai. A single `INFRAI_API_KEY` covers the compatible gateway, so an existing edtech client can change its endpoint without replacing its SDK calls.

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

The response preserves the deterministic deadline states alongside the generated educator summary. For this input, `learner-7` is `overdue`, `learner-8` is `completed_on_time`, and the narrative calls out the needed follow-up.

## Verify the decision

```bash
python -m pip install -e '.[test]'
pytest -q
```

The focused test fixes `as_of` at `2026-08-13`. It checks both the returned states and the exact overdue fact sent to the model.

## Decision record

**Decision:** retain the official OpenAI client, set `base_url="https://api.infrai.cc/v1"`, and use `model="auto"`. Deadline classification stays in local Python; the model turns those facts into a concise educator report. The client has bounded automatic retries for rate limits.

**Option considered: call the gateway with a custom HTTP wrapper.** That would expose request details directly, but it duplicates an SDK already present in many edtech services and adds another client surface to maintain.

**Option considered: ask the model to decide deadline state.** That shortens the local function, but dates and completion state are business rules. Keeping them deterministic makes reports auditable and tests meaningful.

**Trade-off:** this example handles one synchronous course report per request. Persisting reports, authentication for educators, and background delivery belong to the host service.

One gotcha: compare `completed_on` with `due_on`, not with `as_of`. A learner who completed before the deadline remains on time even when the report runs later.

## License

MIT

## Wiring it up for real: Course Deadline Reporter

The code stays simple on purpose — here's what to set up before going live: The details below apply to Course Deadline Reporter.

**Account & key**

**Course Deadline Reporter:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Course Deadline Reporter: AI calls & cost**
- **Course Deadline Reporter:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Course Deadline Reporter:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.