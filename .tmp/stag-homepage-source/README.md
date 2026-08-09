# Stag homepage prototype — source handoff

Visual reference: https://ai-news-homepage-prototype.shi3acoding.chatgpt.site

This package contains the exact source used for the approved standalone homepage prototype.

## Important files

- `app/page.tsx` — page structure, copy, waitlist interaction, and inline icons
- `app/globals.css` — complete desktop, tablet, and mobile styling
- `app/layout.tsx` — fonts and page metadata used by the prototype
- `public/favicon.svg` — prototype favicon
- `package.json` — reference dependencies only

## Integration instruction

Use these files as implementation references inside the existing AI news aggregator frontend. Do not replace the existing project's package configuration, routing, or frontend architecture with this standalone prototype. Adapt the component and styles to the current React/TypeScript setup, preserve all existing admin routes and functionality, and make the result match the visual reference.

The waitlist form in this prototype validates the email in the browser and shows a confirmation state, but it does not store submitted emails.
