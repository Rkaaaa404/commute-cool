---
name: frontend-design
description: Guidelines for high-quality frontend design, UI/UX consistency, mobile responsiveness, mapping visualization, and styling rules for the COMMUTE-COOL dashboard and map interface.
---

# Frontend Design & UI/UX Best Practices

## Overview

This skill outlines guidelines and standards for creating and maintaining visually stunning, highly performant, and responsive frontends. In the context of COMMUTE-COOL, this governs MapLibre GL JS maps, responsive dashboard components, and interactive layouts using HTML, Vanilla CSS, and Vanilla Javascript.

---

## 1. Design & Aesthetic Standards

* **Aesthetic Polish**: Interface should be clean, professional, and visually engaging. Use subtle shadows, border radii, modern typography (e.g., Inter, Outfit, or standard sans-serif system fonts), and appropriate spacing.
* **Responsive Layouts**: Design mobile-first. Interactive elements must be easily clickable on mobile screens (touch targets at least 44x44px).
* **Transitions & Animations**: Use smooth CSS transitions (`transition: all 0.3s ease;`) for hover states, button clicks, and panel slide-ins/fade-ins. Avoid sudden layout jumps.
* **No Placeholders**: Never use placeholder text or empty charts. Use realistic mockup datasets or loading skeletons until data is fetched.

---

## 2. COMMUTE-COOL Mapping Visualization

* **MapLibre GL JS with OpenFreeMap**: Utilize MapLibre GL JS for interactive mapping. Ensure map styles load reliably from OpenFreeMap without API keys or payments.
* **Thermal Comfort Score (TCS) Color Coding**:
  * **Green** (`#2ecc71` or similar modern green): TCS > 0.7 (comfortable, shaded).
  * **Yellow/Orange** (`#f39c12` or similar): TCS 0.4 - 0.7 (moderate, partially shaded).
  * **Red** (`#e74c3c` or similar): TCS < 0.4 (uncomfortable, direct sun).
* **Dual-Layer Heatmap Overlay**:
  * **Glow Layer**: Set `line-blur: 3px` and dynamic `line-width` (6px at zoom 12 scaling to 14px at zoom 16) for glowing visual effects.
  * **Crisp Line Layer**: Set sharp `line-width` (2px at zoom 12 scaling to 5px at zoom 16) for precise spatial reference.
* **Interactive Elements**:
  * Implement clear popups showing the segment ID, TCS value (formatted to 2 decimal places), and thermal comfort category (Red/Yellow/Green).
  * Provide a legend panel with toggle checkboxes to dynamically show/hide the layers.

---

## 3. Styling & Code Organization

* **CSS Custom Properties**: Define theme variables (colors, fonts, sizes) in `:root` for consistency and easy customization.
* **Grid and Flexbox**: Use modern layout engines (CSS Grid and Flexbox) for layout structure instead of outdated float/position hacks.
* **Vanilla Approach**: Prioritize pure CSS and Vanilla JS for performance and flexibility. Only introduce frameworks if explicitly instructed. Avoid using TailwindCSS unless confirmed.
* **Cross-Browser Styling**: Standardize styles across browsers. Ensure layout coordinates (margins, padding, box-sizing) prevent container overflow (`box-sizing: border-box`).

---

## 4. UI States & Feedback

* **Loading States**: Add spinner animations or skeleton components to inform users that data is being loaded.
* **Error Fallbacks**: If API requests fail (e.g., thermal segments or route APIs), gracefully degrade performance (log to console, show map without heatmap, or display demo/fallback route data) rather than rendering broken components.
* **Tooltips and Popovers**: Use semantic HTML with descriptive aria attributes (`aria-label`, `aria-describedby`) for accessible custom widgets.
