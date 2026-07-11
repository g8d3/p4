# higgsfield.ai — API Endpoints

## Authentication

All API calls require:
```
Authorization: Bearer <token>
Content-Type: application/json
Origin: https://higgsfield.ai
Referer: https://higgsfield.ai/
```

Token extracted from browser: `window.Clerk.session.getToken()`

## Image Generation

### Create Job
```
POST https://fnf-api-gw.higgsfield.ai/fnf/jobs/<model_id>
```

Request body:
```json
{
  "params": {
    "model": "<model_id>",
    "prompt": "<text>",
    "width": 1024,
    "height": 1024,
    "quality": "basic",
    "input_images": [],
    "batch_size": 1,
    "aspect_ratio": "1:1",
    "use_unlim": false,
    "seed": <random>
  },
  "use_unlim": false
}
```

### Parameters

| Param | Type | Values | Notes |
|-------|------|--------|-------|
| model | string | See models list | Required |
| prompt | string | Free text | Required |
| width | int | 512-4096 | Default: 1024 |
| height | int | 512-4096 | Default: 1024 |
| quality | string | basic, high | |
| input_images | array | URLs or base64 | For image-to-image |
| batch_size | int | 1-4 | Number of images |
| aspect_ratio | string | 1:1, 3:4, 4:3, 9:16, 16:9, 2:3, 3:2, 21:9 | |
| use_unlim | bool | true/false | Unlimited mode |
| seed | int | Random | Reproducibility |

### Response
Returns job object with ID for polling.

### Poll Status
```
GET https://fnf-api-gw.higgsfield.ai/fnf/jobs/<job_id>/status
```

## List Available Models
```
GET https://fnf-api-gw.higgsfield.ai/fnf/jobs/accessible?job_set_type=<type>&size=50
```

## User Data
```
GET https://fnf-api-gw.higgsfield.ai/fnf/user
GET https://fnf-api-gw.higgsfield.ai/fnf/user/meta
GET https://fnf-api-gw.higgsfield.ai/fnf/user/features
GET https://fnf-api-gw.higgsfield.ai/fnf/user/settings
GET https://fnf-api-gw.higgsfield.ai/fnf/user/profile
```

## Workspaces
```
GET https://fnf-api-gw.higgsfield.ai/fnf/workspaces
GET https://fnf-api-gw.higgsfield.ai/fnf/workspaces/wallet
GET https://fnf-api-gw.higgsfield.ai/fnf/workspaces/subscription
GET https://fnf-api-gw.higgsfield.ai/fnf/workspaces/details
POST https://fnf-api-gw.higgsfield.ai/fnf/workspaces/context
```

## Other
```
GET https://fnf-api-gw.higgsfield.ai/fnf/tours
GET https://fnf-api-gw.higgsfield.ai/fnf/feedback/nps
GET https://fnf-api-gw.higgsfield.ai/fnf/job-sets/costs
GET https://fnf-api-gw.higgsfield.ai/fnf/subscriptions/v2/plans
GET https://fnf-api-gw.higgsfield.ai/fnf/gifts?size=20&type=inbound&activated=false
GET https://fnf-api-gw.higgsfield.ai/fnf/concurrent-boost-credits/state
GET https://fnf-api-gw.higgsfield.ai/fnf/user/offers
GET https://fnf-api-gw.higgsfield.ai/fnf/user/personal-promo
GET https://fnf-api-gw.higgsfield.ai/fnf/referral
GET https://fnf-api-gw.higgsfield.ai/fnf/photo-dump/packs?version=v2
GET https://fnf-api-gw.higgsfield.ai/fnf/custom-references/v2?size=30
GET https://fnf-api-gw.higgsfield.ai/fnf/v2/reference-elements/pinned
GET https://fnf-api-gw.higgsfield.ai/fnf/v2/reference-elements/picker?size=10
GET https://fnf-api-gw.higgsfield.ai/fnf/v2/quizzes/user
GET https://fnf-api-gw.higgsfield.ai/fnf/v2/auto-top-ups/settings
GET https://fnf-api-gw.higgsfield.ai/fnf/user/credit-package-discount
GET https://fnf-api-gw.higgsfield.ai/fnf/cashback-challenge
GET https://fnf-api-gw.higgsfield.ai/fnf/user/free-gens/v2
GET https://fnf-api-gw.higgsfield.ai/fnf/user/personal-promo/tasks
GET https://fnf-api-gw.higgsfield.ai/fnf/workspaces/unlim-activations
GET https://fnf-api-gw.higgsfield.ai/fnf/folders/null/info?size=10
POST https://fnf-api-gw.higgsfield.ai/fnf/favourites/liked-by/v2
GET https://fnf-api-gw.higgsfield.ai/fnf/supercomputer/storage/usage
GET https://fnf-api-gw.higgsfield.ai/fnf-notification/notifications?limit=20
GET https://fnf-api-gw.higgsfield.ai/fnf-notification/notifications/stream
GET https://fnf-api-gw.higgsfield.ai/fnf-score/v1/rewards/summary
```

## Notes

- OPTIONS preflight may return 403 (DataDome) even if POST works
- Some endpoints require specific subscription tier
- Rate limiting may apply
