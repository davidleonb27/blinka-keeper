# Blinka Design System

> Category: Fintech / B2B banking · Surface: web (marketing + product UI)
> Source: faithful clone of https://blinka.co (`blinka-clone.html`, `assets/main-CqMgimik.css`).

## 1. Context

Blinka is "the banking platform for global companies": USD accounts, global payments, Visa Infinite cards, and high-yield treasury. Blinka Tech Corp is a fintech, not a bank. Banking comes from Portage Bank (Member FDIC), cards from Third National, treasury from Atomic Invest. Backed by Y Combinator. Audience: finance and ops leads at cross-border companies, mainly LatAm. Evidence: `RECON/index.md`, `RECON/screenshots/`, `blinka-clone.html`.

## 2. Visual theme

Calm, precise, institutional. Warm off-white paper (`#f7f7f4`) with navy ink, one cobalt accent, hairline borders, and one engraved line-art hero illustration (`assets/blinka-engraving-CO_0wrzm.svg`). Product UI appears as soft floating cards with long, low-opacity shadows. Page ends in a deep night section (`#111720`) for onboarding and legal footer.

## 3. Color

| Token | Value | Use |
|---|---|---|
| `--bk-ink` | `#1c253a` | Text, default button |
| `--bk-muted` | `#656975` | Secondary text, eyebrows, disclosures |
| `--bk-paper` | `#f7f7f4` | Page background |
| `--bk-accent` | `#2a4bd0` | Primary CTA, selected state |
| `--bk-line` | `#dedfdc` | Hairlines |
| `--bk-night` | `#111720` | Dark sections |
| `--bk-night-ink` / `--bk-night-muted` | `#e9edf1` / `#b2bbc7` | Text on night |
| `--bk-accent-soft` | `#b9c8ff` | Accent on dark |

Accent is used sparingly: CTA, selection, focus. Nav links `#505563`.

## 4. Typography

- Sans: Inter variable, family `Blinka Inter` (`fonts/inter-latin-variable-Dx4kXJAl.woff2`).
- Mono: Geist Mono Variable for numerals, codes, tickers (`fonts/geist-mono-latin-wght-normal-XN7g48iV.woff2`).
- H1 `clamp(48px, 4.4vw, 63px)`, weight 450, line-height 1.07, tracking -0.047em. 390px: ~31-49px.
- Eyebrow: 11px, 500, uppercase, tracking 0.1em, muted.
- Body 13-15px; legal/disclosure 11px / 1.7. Nav 13px.

## 5. Spacing and radius

Container `min(1180px, 100% - 96px)`; 48px gutters at tablet, 40px at mobile. Hero padding 66/43px. Sections separated by generous 80-150px. Radius: pill 999 (buttons), 20/16/12 (cards), 8 (chips), 2 (flag/tag). Shadows: `--bk-shadow-sm/md/lg` in `colors_and_type.css`.

## 6. Layout

Sticky header with 14px backdrop blur on `rgba(247,247,244,.93)`; header theme flips on dark sections. Hero: left copy (max 680px) over right engraving. Customer logo marquee. Product bento: one wide account card, two half cards (card, treasury). Global payments: route lists left, dotted globe right. Back office accordions. Dark onboarding quiz, then dark legal footer with numbered disclosures.

## 7. Components

- **Button** — pill, 48px min-height (38px small), ink default, accent primary, arrow glyph gap 25px. Hover darkens/swaps to accent; focus ring 2px accent.
- **Header** — wordmark, 4 text links, "Sign in" text link + small pill CTA.
- **Eyebrow** — uppercase muted label above headings.
- **Product card** — white surface, radius 16-20, md shadow, mono amounts, status chip.
- **Route list** — flag, currency code in mono, rail name.
- **Quiz option** — dark rounded row with radio, accent on select; Continue disabled until both answered.
- **Accordion** — hairline rows with +/− icon.
- **Disclosure** — 11px muted, numbered markers.
- **Client logo marquee** — 105×30 marks, paused control.

## 8. Motion

Transitions 0.16-0.18s on color, background, shadow. Marquee with pause button. Scroll-driven header theme. Respect `prefers-reduced-motion`.

## 9. Voice

Plain, confident, short sentences with periods ("Global payments."). Sentence case headings. Always pair claims with regulator-aware disclosures. Say "USD account", "Visa Infinite", "Treasury". Never imply Blinka is a bank.

## 10. Anti-patterns

- No purple/neon gradients, glassy fintech gloss, or emoji icons.
- No second solid CTA near the first; one primary per viewport.
- No bank/FDIC claims without the Portage Bank qualifier; no card art as final (it is provisional).
- No invented metrics beyond the source's $-example amounts.
- Don't use accent as a background fill for large areas.
- Don't reimplement partner marks (Visa, BNY, Morgan Stanley); use preserved files in `assets/`.

## Package map

`colors_and_type.css` tokens · `assets/` real logos/images · `fonts/` font files · `preview/` review cards · `ui_kits/app/` applied kit · `examples/` preserved source HTML/CSS · `RECON/` evidence · provenance in `context/source-context.md` and `NOTES.md`.
