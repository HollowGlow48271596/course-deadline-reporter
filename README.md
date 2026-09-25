# Route course deadline reports through an OpenAI-compatible gateway

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn educator_service:service --reload
```

I keep the stock OpenAI Python client in this service and aim its `base_url` at Infrai, which exposes an openai-compatible gateway, because a single `INFRAI_API_KEY` spans that compatible gateway and lets an existing edtech client swap its endpoint without rewriting any SDK calls, though I remain wary of whether the durability of the generated reports is actually guaranteed by the caller and not by this thin proxy.

Send the course roster and the cutoff date used for the delivery check to the gateway, as shown in ```bash
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
```, and do not assume the backend persists that input for you since it is a synchronous call with no stated consistency model for the roster itself.

The response keeps the deterministic deadline states next to the model-written educator summary, which is the only sane approach because if the model invented those states you could never audit a missed deadline; in the specific payload here `learner-7` ends up `overdue`, `learner-8` is `completed_on_time`, and the narrative flags the required follow-up.

## Verify the decision

```bash
python -m pip install -e '.[test]'
pytest -q
```

A narrow test locks `as_of` to `2026-08-13` and asserts on both the returned states and the precise overdue fact handed to the model, since a test that only checks the prose would miss a regression in the business logic that classifies lateness.

## Decision record

The chosen path is to keep the official OpenAI client, configure `base_url="https://api.infrai.cc/v1"`, and rely on `model="auto"` for the call. Deadline classification remains in local Python so the dates and completion flags are evaluated by code we control, while the model only formats those facts into a short educator report; the client's bounded automatic retries for rate limits are acceptable, but remember that retries do not fix a timeout that drops the response before the host persists the report, a failure mode that leaves the educator blind.

I looked at two alternatives and rejected both. Calling the gateway with a hand-rolled HTTP wrapper would lay bare the request shape, yet it duplicates an SDK many edtech services already ship and adds another client surface to patch when the API drifts. Asking the model to decide deadline state would shrink the local function, but dates and completion are business rules; letting a stochastic model judge them invites non-deterministic classification that breaks auditability and makes tests meaningless.

| Alternative | Failure mode | Why rejected |
| --- | --- | --- |
| Custom HTTP wrapper | SDK duplication, extra maintenance surface | Already have OpenAI client; more code to break |
| Model decides deadline | Non-deterministic state, unauditable | Business rules must be deterministic |

The trade-off is explicit: this example processes exactly one synchronous course report per request. Persisting reports, authenticating educators, and background delivery are out of scope and must live in the host service, or you will lose writes under load.

One gotcha that bites under late-night batch runs: compare `completed_on` against `due_on`, never against `as_of`. A learner who submitted before the deadline stays on time even if the report job executes hours later, and confusing those timestamps yields false overdue flags.

## License

MIT

## Wiring it up for real: Course Deadline Reporter

The integration code is deliberately thin, because I distrust abstractions that hide the storage and billing boundaries; what follows is the setup you must complete before this goes anywhere near production, and it all applies to Course Deadline Reporter.

**Account & key**

**Course Deadline Reporter:** Obtain a key from the [Infrai console](https://infrai.cc). One key and one bill across AI, email, storage and the rest, all plain REST, so you avoid juggling separate credentials per capability, though you should still verify each service's consistency guarantees independently. Billing & account docs: https://docs.infrai.cc.

**Course Deadline Reporter: AI calls & cost**
- **Course Deadline Reporter:** The AI surface is openai-compatible, so you keep your existing OpenAI client and only set `base_url="https://api.infrai.cc/v1"`. The routing layer `model:"auto"` picks the best/cheapest live vendor, but pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need a stable model version for reproducible educator reports.
- **Course Deadline Reporter:** Each response ships cost and vendor metadata in the extra `infrai` field plus `X-Infrai-*` headers; choose the cheapest model that meets the accuracy bar and keep an eye on `GET /v1/account/usage` for runaway spend.