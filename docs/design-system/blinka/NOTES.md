# blinka.co clone

- Source: https://blinka.co/ (Vite + React, prerendered HTML, no source repo found; fetched deployed HTML via curl)
- Mode: faithful clone of prerendered HTML. CSS, fonts (Inter, Geist Mono), logos and images are the real deployed files, stored locally in `assets/`.
- Entry: `blinka-clone.html`. Untouched original: `RECON/original.html`. Version with the JS bundle: `RECON/clone-with-bundle.html`.
- Tracking: none found in HTML or JS.

## Known gaps
- Browser recon scripts could not run (sandbox blocked the Chrome temp profile), so no route crawl, interaction probe, or pixel diff. Verification = one rendered export (`RECON/clone-1440.png`) plus static checks.
- The React bundle is removed: the page rendered blank with it. Cause not diagnosed. Interactive parts (payment route selector, onboarding quiz, accordions, customer marquee, scroll-driven header theme) are static.
- Booking section loads cal.com in the original; not wired here.
- "Sign in" and "Get started" still point to app.blinka.co.

## Replace before deploying
Blinka name, logos, partner logos (Didit, Braven, Lazo, Dapta, Macondo, Talentropy, Signa, Creditop), Visa/Morgan Stanley/BNY marks, legal and disclosure copy. All belong to their owners.
