# higgsfield.ai

AI-native creative suite for image, video, and audio generation.

## URL Structure

| Page | URL | Purpose |
|------|-----|---------|
| Image generation | `/ai/image?model=<id>` | Text-to-image |
| Video generation | `/ai/video` | Text-to-video |
| Audio | `/audio` | Music/audio generation |
| Supercomputer | `/supercomputer` | AI agent (planning, multi-step) |
| Cinema Studio | `/generate` | Cinematic video creation |
| Marketing Studio | `/marketing-studio/product` | Marketing content |
| Shorts Studio | `/shorts-studio` | Short-form video |
| Explainer | `/explainer` | Explainer videos |
| Originals | `/original-series` | Custom characters |
| Canvas | `/canvas` | Collaborative editing |
| AI Influencer | `/ai-influencer-studio` | Virtual influencers |
| Apps | `/supercomputer/apps` | Community apps |
| Assets | `/asset/all` | User's generated content |
| Library | `/library/image` | Generated images history |
| Profile | `/@username` | User profile |
| Pricing | `/pricing` | Subscription plans |

## Backend Services

| Service | Domain | Purpose |
|---------|--------|---------|
| Main API | fnf.higgsfield.ai | User data, workspaces, settings |
| API Gateway | fnf-api-gw.higgsfield.ai | Job creation, authenticated endpoints |
| CMS | cms.higgsfield.ai | Content, notices |
| Pricing | pricing.higgsfield.ai | Plans, pricing config |
| Auth | clerk.higgsfield.ai | Authentication (Clerk) |
| Analytics | amplitude.higgsfield.ai | Event tracking |
| CDN | cdn.higgsfield.ai | Media files |
| Images | images.higgsfield.ai | Image proxy/transforms |
| DataDome | geo.captcha-delivery.com | Bot protection |

## Known Issues

- **DataDome protection**: Blocks headless browsers. OPTIONS preflight may return 403.
- **User-Agent detection**: Chrome headless shows "HeadlessChrome" which DataDome detects.
- **CAPTCHA**: DataDome may show CAPTCHA challenge at any time.
- **Session**: Requires login. Clerk session tokens expire.

## Authentication

- Clerk-based auth (clerk.higgsfield.ai)
- Token: `window.Clerk.session.getToken()`
- Stored in cookies (__session)
- Session ID: `window.Clerk.session.id`
