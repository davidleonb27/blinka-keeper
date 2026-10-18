# Blinka applied UI kit

Applied interface kit rebuilt from the blinka.co landing page (`blinka-clone.html`, `RECON/screenshots/original-1440.png`).

## Structure

- `index.html` — App shell: full page markup. It embeds the styles from `components/components.css` so it opens standalone.
- `components/components.css` — editable styles for header, hero, PreviewCard-style panels, option rows, route buttons, accordion, night quiz and footer.
- `app.js` — behavior: radio groups (treasury fund, quiz), payment route selector, accordion, quiz gating.

## Components

App page order: sticky header, hero with engraving, account card, Visa Infinite panel, treasury fund picker, payment route selector (updates currency and rail), back-office accordion, onboarding Composer-style quiz (Continue enables after both answers), numbered disclosure footer.

## Usage

Open `index.html` (paths use `../../colors_and_type.css` and `../../assets/`). To reuse a section, copy its markup plus the matching classes from `components/components.css`, keep the `--bk-*` tokens linked, and use `app.js` for interactions. Keep one primary CTA per viewport and keep disclosures next to FDIC, card and treasury claims.

## Design Notes

Source basis: `RECON/index.md` for copy and structure, `assets/main-CqMgimik.css` for values, `DESIGN.md` for rules. Colors and typography come only from `colors_and_type.css` tokens. Focus rings are 2px accent (accent-soft on night). Layout collapses to one column below 760px.
