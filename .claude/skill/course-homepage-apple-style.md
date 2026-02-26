---
name: course-homepage-apple-style
description: Build an Apple-like landing homepage for this course project with smooth color transitions, course-relevant motion, and seamless scroll entry to the lecture portal while keeping bottom navigation.
---

# Course Homepage Skill (Apple-style, course-themed)

## Goal

Create a premium landing page at project root (`index.html`) that:
- visually matches existing lecture palette (`--accent-primary`, warm dark/light theme),
- uses smooth gradients and subtle motion (no abrupt blocks),
- supports mobile-first viewing,
- scrolls down into the existing first page experience (`html/index.html`),
- keeps a persistent glass-style bottom navigation.

## Visual Rules

1. **Palette consistency**
   - Reuse existing warm academic colors from portal/interactive pages.
   - Avoid introducing unrelated neon or overly saturated colors.

2. **Transition quality**
   - Use layered radial/linear gradients between sections.
   - Keep transitions continuous across sections (no hard cut unless intentional).

3. **Motion quality**
   - Prefer low-amplitude floating/parallax/glow motion.
   - Use `transform` + `opacity` for performance.
   - Add `prefers-reduced-motion` fallback.

4. **Content relevance**
   - Hero messaging should reflect course scope: FinTech, AI, ML lectures, notes, quizzes, PDF reading.
   - Decorative visuals should map to learning themes (network, chart, concept flow), not random stock graphics.

## Interaction Rules

1. Provide scroll cue from hero to next section.
2. Next section should naturally lead users into current portal (`html/index.html`) via embedded preview or direct transition.
3. Keep bottom nav visible and usable on mobile/desktop.
4. Ensure links work under both:
   - local server root (`/`)
   - GitHub Pages project subpath (`/<repo>/`).

## Verification Checklist

- `index.html` opens correctly and shows hero + transition section.
- Scrolling down reaches the portal-entry section without broken layout.
- Bottom nav stays visible and interactive.
- Color style remains consistent with existing lecture pages.
- `bash scripts/check_project.sh` passes.

