# Blinka Design System

## Product Overview

Blinka is a banking platform for global companies (blinka.co). The product provides USD accounts over ACH and wire, global payments with SWIFT and local rails (SPEI, Pix, SEPA, Bre-B, USDC), Visa Infinite business cards with no FX markup, high-yield Treasury funds, and a financial back office for invoicing, vendors and accounting. Blinka Tech Corp is a fintech, not a bank; banking is provided by Portage Bank, Member FDIC. Primary surfaces: the marketing site, product cards, a payments route selector, an onboarding quiz and a legal disclosure footer.

## Source Context

Source evidence and context references:

- `context/source-context.md` — project handoff and copied file list.
- `RECON/index.md`, `RECON/original.html`, `RECON/screenshots/` — recon of blinka.co at 390, 768 and 1440px.
- `NOTES.md` — clone notes and known gaps (no pixel diff; JS interactions were static in the clone).
- `blinka-clone.html` — faithful clone; preserved copies in `examples/`.

## Package Contents

- `DESIGN.md` — rules: context, color, type, spacing, layout, components, motion, voice, anti-patterns.
- `SKILL.md` — agent usage instructions.
- `colors_and_type.css` — tokens, base typography, button.
- `assets/blinka_logo_white_mode-DaeD_jLH.svg` and the rest of `assets/` — preserved brand logos, partner marks, engraving, Visa Infinite card art, source CSS/JS bundle.
- `fonts/inter-latin-variable-Dx4kXJAl.woff2` and Geist Mono — Inter variable and Geist Mono (latin) font files. No `build/` runtime icons exist in the evidence.
- `favicons/` — favicon set and webmanifest.
- `examples/` — `blinka-landing-source.html`, `blinka-source.css` (preserved source).
- `preview/` — focused review cards (manifest below).
- `ui_kits/app/` — applied interface kit (see its README).

## Preview Manifest

- `preview/colors-primary.html` — core palette.
- `preview/colors-night.html` — night section and accent tints.
- `preview/typography-specimens.html` — H1, H2, eyebrow, mono numerals, disclosure.
- `preview/spacing-tokens.html` — spacing scale and container.
- `preview/radius-shadows.html` — radius and shadow tokens.
- `preview/components-buttons.html` — pill buttons and states.
- `preview/components-cards.html` — account and treasury cards.
- `preview/brand-assets.html` — wordmarks, favicon, partner logos, card art.
- `preview/applied-surface.html` — hero with engraving.

## Review Workflow

1. Open `preview/colors-primary.html` and `preview/typography-specimens.html`.
2. Open `preview/components-buttons.html` and `preview/applied-surface.html`.
3. Open `ui_kits/app/index.html` and try treasury funds, route buttons, accordion and quiz.

## Reuse Workflow

1. Start with `DESIGN.md`, then load `colors_and_type.css`; use `--bk-*` tokens only.
2. Copy sections from `ui_kits/app/index.html`.
3. Pull logos and images from `assets/` and fonts from `fonts/`; never redraw partner marks.
4. Check results against `DESIGN.md` section 10 (anti-patterns).

Partner marks (Visa, BNY, Morgan Stanley, customer logos) belong to their owners.
