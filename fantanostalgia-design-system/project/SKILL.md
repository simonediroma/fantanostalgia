---
name: fantanostalgia-design
description: Use this skill to generate well-branded interfaces and assets for FantaNostalgia, either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping the 8-bit Sensible Soccer aesthetic.
user-invocable: true
---

Read the README.md file within this skill, and explore the other available files.
If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.
If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

Key design rules to follow:
- Language: Italian. All UI copy in Italian.
- Font: Press Start 2P for headings/labels/buttons (UPPERCASE only), Courier New for body/data.
- Colors: bg #050510, surface #0d0d2b, accent #ffe600 (yellow), accent2 #00d4ff (cyan), green #00ff55, red #ff1144.
- Zero border-radius on everything. Pixel box-shadows (no blur). CRT scanline overlay via body::before.
- Hover: accent → accent2 (instant, no CSS transition).
- Components are in window.DesignSystem_90de16 — use the bundle if available.
