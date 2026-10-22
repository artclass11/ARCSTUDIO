# ARCSTUDIO91 Daily Publisher

Free daily architecture-carousel workflow for @arcstudio91. It uses Python/Pillow and reusable photographs from Wikimedia Commons to create four separate 1080x1350 images and can publish to Instagram and a connected Facebook Page through Meta's official Graph API.

## Daily behaviour

- Runs around 08:07 India time (02:37 UTC).
- Rotates original concepts across 10 editorial pillars: design studies; climate-wise living; space planning; durability and repairability; people-first places; adaptive reuse; interiors and sensory design; landscape and water; architecture explainers; and design decision stories.
- Includes residential, apartment, villa, office, healthcare, education, hospitality, retail, public-space, landscape and retrofit typologies, plus practical lessons on wayfinding, acoustics, daylight, maintenance, materials and water.
- Records concept date, pillar, headline, core insight and visual motif in `data/concept_history.json`; the selector avoids recently used concepts for up to 30 prior entries when alternatives exist.
- Caption tone aims for useful, save-worthy education and one natural discussion prompt—not clickbait, fake project claims or hashtag stuffing.
- Uses Wikimedia Commons photographs only when a reusable licence is verifiable, and includes attribution in the bilingual caption.
- Creates exactly four separate 1080×1350 JPG slides plus PNG masters and a review-only contact sheet (never a publishable 2×2 collage). Images are full-bleed, text is minimal, and phone details appear only on slide 4.
- Adds a varied, date-rotated discussion prompt to the caption and generates source/licence notes plus a quality manifest for review.
- Commits images to this public repo so Meta can fetch them over HTTPS.
- Publishes an Instagram carousel and a Facebook Page multi-photo post only when explicitly enabled.
- Tracks publish state and refuses automatic retries after an ambiguous publish response.
- Uses free tools only. No paid image credits, Metricool or Windsor.ai. The daily workflow is scheduled for approximately 08:07 India time; generation is separate from actual platform publishing.

Reference photos are inspirational examples and are not represented as completed ARCSTUDIO91 projects. If suitable licensed images are unavailable, generation fails safely and no post is published.

## One-time Meta setup

1. Confirm @arcstudio91 is an Instagram Professional (Business or Creator) account linked to the Facebook Page you own/manage.
2. In Meta for Developers, create/select an app and configure Instagram API with Facebook Login.
3. Authorize the app for these permissions as required by Meta: instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement, and pages_manage_posts. Complete any required Page Publishing Authorization or access approval. Official references: https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api and https://developers.facebook.com/documentation/pages-api/posts
4. Get the numeric Instagram Professional Account ID, numeric Facebook Page ID, and a Page access token authorized for the linked Page. Never put tokens in code, issues, commits or chat.
5. In repository Settings → Secrets and variables → Actions → Secrets, add:
   - IG_USER_ID — numeric Instagram Professional Account ID.
   - META_PAGE_ID — numeric Facebook Page ID.
   - META_PAGE_ACCESS_TOKEN — Page access token with the required permissions.
6. Under Settings → Secrets and variables → Actions → Variables, add AUTO_PUBLISH_ENABLED with value YES.

Publishing is OFF until AUTO_PUBLISH_ENABLED is set to YES. The workflow still builds the daily carousel and uploads an Actions artifact while publishing is off.

## Test and operate

- Open Actions → ARCSTUDIO91 Daily Architecture → Run workflow while publishing is still off. Inspect the four images, caption and photo credits.
- Only after the correct accounts and permissions are verified, add the secrets and set AUTO_PUBLISH_ENABLED to YES.
- A successful run records IDs/status in data/publish_state.json. Verify the actual Instagram post and Facebook Page post.
- If a final publish response is ambiguous, the state is marked needs_review. Inspect the platform before any manual retry.
- Meta tokens can expire or be revoked. If an authentication error occurs, re-authorize and replace the repository secret.

## Brand rules

Use the public @arcstudio91 profile as broad stylistic inspiration only when accessible; never copy distinctive layouts, captions, plans, renders or projects. The principles remain minimal functionality, low maintenance, practical security/safety and sustainability. A 100-year lifecycle is an aspiration, never a guarantee.

Caption is in Marathi and English, with services and photo attribution. Contact details appear only on slide 4: +91 9921894495. Account passwords and session cookies are not used.
