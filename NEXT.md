# Next Session

## Priority 1 — Card layout v2 (multi-scene support)

Current `card.py` hardcodes 3 scenes in a horizontal strip. Dream #003
produced 4 scenes; scene 4 is archived but unused in the card.

- Add layout mode switch based on len(scenes):
  - 2 scenes: larger images, side-by-side
  - 3 scenes: current horizontal strip
  - 4 scenes: 2x2 grid
  - 5 scenes: vertical stack with cropped aspect
- Adjust font sizes and padding based on layout mode
- Test on Dream #003 (4 scenes) — should now include the bonus scene

## Priority 2 — Collect 2-3 more real dreams

Target archetype coverage:
- [x] Shadow (Dream #001)
- [x] Self (Dream #002)
- [x] Trickster (Dream #003, fictional)
- [ ] Anima or Animus
- [ ] Puer Aeternus (child/wonder)
- [ ] Great Mother (nurturing/devouring)
- [ ] Hero (quest/transformation)

Method: Telegram voice note first thing in the morning → afternoon pipeline
run → archived card.

## Priority 3 — Simple HTML gallery

Goal: One scrollable page showing all cards in a grid, Oneiric logo header,
footer linking to repo. Vercel deploy.

- Stack: plain HTML + Tailwind CDN, no framework
- Data source: gallery/data/dreams.json
- Each card: thumbnail (card.png), title, mood chip, archetype chip
- Click opens card.png in a lightbox modal
- Mobile-first (9:16 cards display naturally)

## Priority 4 — Demo video (2 min)

Storyboard target:
- 0:00-0:15  Hook: "What if your dreams became portable artworks?"
- 0:15-0:45  Record a voice note on Telegram, pipeline runs (screen capture)
- 0:45-1:15  Card reveal, scroll through details
- 1:15-1:45  Show gallery with 3-5 dream cards side by side
- 1:45-2:00  "Built on Hermes Agent by Nous Research." + repo link

## Open questions
- Should the card also embed a small QR code linking to the gallery?
- Should we support re-using a cached analysis while regenerating images
  (style iteration)?
