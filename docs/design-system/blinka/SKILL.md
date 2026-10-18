---
name: blinka-design-system
description: Blinka fintech design system (blinka.co). Use for Blinka-branded marketing pages, account/treasury cards, payment route selectors, onboarding quiz and legal footers.
user-invocable: true
---

# Blinka design system

## What is inside

`DESIGN.md` (rules), `colors_and_type.css` (tokens), `assets/` (real logos, engraving, card art), `fonts/` (Inter, Geist Mono), `preview/` (9 review cards), `ui_kits/app/` (applied kit), `examples/` (source HTML/CSS), `RECON/` (evidence).

## Source context

Faithful clone of https://blinka.co, a Vite + React site for a fintech offering USD accounts, global payments, Visa Infinite cards and Treasury. Evidence in `RECON/index.md`, `RECON/screenshots/`, `context/source-context.md`.

## When to use

Any UI that must look like Blinka: landing sections, product cards, onboarding flows, disclosure-heavy footers.

## How to use

1. Read `DESIGN.md`; link `colors_and_type.css` and use `--bk-*` tokens only.
2. Page: `--bk-paper` background, `--bk-ink` text, one cobalt `--bk-accent`. Use `--bk-night` only for onboarding and footer.
3. Headings in Blinka Inter weight 450 with tight tracking; numerals and codes in Geist Mono.
4. One primary pill CTA per viewport ("Get started"); everything else is secondary or a text link.
5. Use real files from `assets/` (`blinka_logo_*`, `blinka-engraving`, `blinka-visa-infinite`, partner logos).
6. Include disclosures for FDIC, card, treasury and stablecoin claims (copy in `RECON/index.md`).
7. Start from `ui_kits/app/index.html`.

## Highlights

- Warm paper `#f7f7f4`, ink `#1c253a`, accent `#2a4bd0`, night `#111720`.
- Pill buttons (48px), 16-20px card radius, long soft shadows, hairline `#dedfdc` borders.
- Container `min(1180px, 100% - 96px)`; sticky blurred header.
- Voice: short, plain sentences with periods; never imply Blinka is a bank.
