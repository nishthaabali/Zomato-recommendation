---
name: Bangalore Dining Discovery
colors:
  surface: '#131316'
  surface-dim: '#131316'
  surface-bright: '#39393c'
  surface-container-lowest: '#0e0e11'
  surface-container-low: '#1b1b1e'
  surface-container: '#1f1f22'
  surface-container-high: '#2a2a2d'
  surface-container-highest: '#353438'
  on-surface: '#e4e1e6'
  on-surface-variant: '#e4bebc'
  inverse-surface: '#e4e1e6'
  inverse-on-surface: '#303033'
  outline: '#ab8987'
  outline-variant: '#5b403f'
  surface-tint: '#ffb3b1'
  primary: '#ffb3b1'
  on-primary: '#680011'
  primary-container: '#ff535a'
  on-primary-container: '#5b000e'
  inverse-primary: '#bb162c'
  secondary: '#ffb957'
  on-secondary: '#462b00'
  secondary-container: '#d98e00'
  on-secondary-container: '#4c2f00'
  tertiary: '#4edea3'
  on-tertiary: '#003824'
  tertiary-container: '#00a572'
  on-tertiary-container: '#00311f'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b1'
  on-primary-fixed: '#410007'
  on-primary-fixed-variant: '#92001c'
  secondary-fixed: '#ffddb5'
  secondary-fixed-dim: '#ffb957'
  on-secondary-fixed: '#2a1800'
  on-secondary-fixed-variant: '#643f00'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#131316'
  on-background: '#e4e1e6'
  surface-variant: '#353438'
typography:
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 26px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: 0em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.03em
  caption:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.25rem
  gutter-sm: 1rem
  gutter-lg: 1.5rem
  margin: 1rem
  margin-md: 1.5rem
  margin-lg: 2.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
---

## Brand & Style

This design system drives an intelligent, sensory-driven dining discovery tool focused on Bangalore's vibrant culinary ecosystem. The personality balances refined nocturnal elegance with hyper-functional computational clarity. It avoids visual clutter, favoring a high-end editorial atmosphere reminiscent of boutique nightlife guides coupled with technical precision.

The emotional goal is decisive confidence and culinary excitement. Interacting with recommendations should feel like consulting an ultra-plugged-in local food curator who knows every neighborhood secret from Indiranagar cocktail lounges to traditional Malleshwaram eateries.

The aesthetic fuses **Modern Dark Minimalism** with **Atmospheric Layering**:
- Deep, ink-charcoal surfaces provide absolute visual calm.
- Controlled culinary accents—crimson and warm amber—punctuate critical discovery cues and AI scoring.
- Crisp 1px borders and gentle micro-glows replace heavy, muddy skeuomorphic drop-shadows.
- Fluid transitions and tactile feedback establish high-craft responsiveness across dense search parameters.

## Colors

The palette is tuned specifically for low-light, high-contrast mobile and desktop usage. Every foreground element meets WCAG AA standards against the deep charcoal foundation.

### Surface Hierarchy
- **Canvas Base (`#0E0E11`):** The primary backdrop behind all views. Absorbs reflection and frames cards with cinematic weight.
- **Surface Level 1 (`#17171C`):** Base container for cards, sheet modals, and navigation panels.
- **Surface Level 2 (`#1F1F26`):** Active states, card hover states, selected filter tags, and elevated tooltips.
- **Border Structural (`#2A2A32`):** Precise 1px hairline rule defining all surface perimeters and internal dividers.
- **Border Interactive (`#E23744` at 40-100%):** Active focus boundaries and highlighted card selections.

### Brand Accents
- **Primary Accent (`#E23744`):** Signature crimson used for primary actions, slider fills, AI confidence pills, and interactive hover glows.
- **Secondary Accent (`#F5A524`):** Warm culinary amber reserved strictly for star ratings, bookmark confirmations, and "Must Try" distinctions.

### Text & Iconography
- **Text Primary (`#F4F4F6`):** Titles, card headings, and active values.
- **Text Secondary (`#A1A1AA`):** Descriptions, metadata (distance, locality), and filter subheadings.
- **Text Muted (`#6B6B76`):** Timestamps, passive footers, and inactive input placeholders.

### Semantic Tints
Informational and AI statuses use low-opacity tinted surface backgrounds (10-12% opacity) bounded by a solid 3px left border:
- **AI Summary / Success:** `#10B981` (Emerald)
- **AI Fallback / Warning:** `#F59E0B` (Amber)
- **Relaxed Filters / Info:** `#3B82F6` (Electric Blue)
- **Critical / Error:** `#EF4444` (Crimson Alert)

## Typography

The pairing combines **Plus Jakarta Sans** for expressive, human-centric geometry in display elements with **Inter** for high-density, neutral body text.

### Font Hierarchy & Roles
- **Display & Headings (Plus Jakarta Sans):** Applied to view titles, recommendation module headings, and restaurant names. Its contemporary curves bring warmth and culinary character while staying modern.
- **Body & Data Attributes (Inter):** Handles long AI review summaries, match criteria breakdowns, price tags, and neighborhood addresses. Provides maximum legibility at 13px and 14px in dark contexts.
- **Badges & Tags (Plus Jakarta Sans SemiBold/Bold):** Used in 12px tags to maintain structural legibility against colored fills and high-contrast badges.

### Editorial Guidelines
- Use tabular figures for price indicators (`₹₹₹₹`), review totals, and kilometer markers.
- Limit uppercase transformations strictly to 11px and 12px status metadata and badge tags with a positive letter spacing of `+0.03em` to `+0.04em`.
- Headings never drop below 600 weight to maintain high visual contrast against dark backgrounds.

## Layout & Spacing

The layout is structured around an adaptive 12-column grid for desktop views and a dynamic single-to-dual column system on smaller form factors, ensuring immediate scanability of food images and data points.

### Screen Adaptations
- **Mobile (< 768px):** Single-column stream with sticky discovery controls and a safe margin of `1rem`. Restaurant cards span full width with unified `1.25rem` vertical separation.
- **Tablet (768px - 1024px):** 6-column grid with `1.5rem` outer margins and `1rem` gutters. Allows dual-card comparison views or split list/map exploratory mode.
- **Desktop (> 1024px):** 12-column grid locked to a max width of `1440px`. Layout allocates 4 columns to AI prompt inputs/preference selectors and 8 columns to the infinite recommendation feed.

### Rhythm Rules
- Component padding strictly relies on `space-sm` (8px) for badge internals, `space-md` (16px) for compact card interiors and input paddings, and `space-lg` (24px) for hero containers.
- Element groupings follow proximity rules: an AI recommendation chip group maintains `0.5rem` between sibling items, while distinct content cards separate by `1.25rem` to `1.5rem`.

## Elevation & Depth

Depth is established via **Tonal Stacking** accompanied by **Subtle Hairline Boundaries** and **Warm Glows**, rather than diffuse gray dropshadows that muddy dark themes.

### Elevation Levels

- **Base Layer (Level 0 - `#0E0E11`):** The viewport foundation. Contains no shadow or elevation.
- **Card & List Tier (Level 1 - `#17171C`):** 
  - Border: `1px solid #2A2A32`
  - Shadow: `0 4px 16px -2px rgba(0, 0, 0, 0.45)`
- **Hover & Active Tier (Level 2 - `#1F1F26`):**
  - Border: `1px solid #3E3E4A` (or `rgba(226, 55, 68, 0.5)` for primary targets)
  - Shadow: `0 8px 24px -4px rgba(0, 0, 0, 0.65)`
- **Floating Overlays & AI Popovers (Level 3 - `#24242D`):**
  - Border: `1px solid rgba(255, 255, 255, 0.08)`
  - Shadow: `0 16px 36px -8px rgba(0, 0, 0, 0.8)`

### Micro-Glow Accentuation
Primary interactive components (active filter pills, primary buttons, price sliders) leverage a specialized crimson luminescent spread:
- **Hover/Focus Glow:** `box-shadow: 0 0 12px 0 rgba(226, 55, 68, 0.35)`
- **Star & Rating Accents:** Ambient badge glow `box-shadow: 0 0 8px 0 rgba(245, 165, 36, 0.25)`

## Shapes

The design system uses deliberate 12px to 16px curvature to humanize the interface, balancing soft contemporary consumer aesthetics with dense computational information.

### Token Application
- **12px (`rounded-md`):** Input fields, inline filter chips, contextual dropdown menus, and internal image thumbnails.
- **16px (`rounded-lg`):** Standard restaurant recommendation cards, AI summary containers, and sliding bottom sheets.
- **24px (`rounded-xl`):** Floating navigation bars, prompt search bars, and modal dialogs.
- **Pill (`rounded-full`):** Floating category tags, rating counter badges, and avatar frames.

## Components

### Buttons
- **Primary:** Background `#E23744`, text `#FFFFFF`, radius 12px. Transitions to a brighter crimson `#EC4855` with a `0 0 16px rgba(226, 55, 68, 0.4)` glow on hover. Active state scales slightly to `0.98`.
- **Secondary / Ghost:** Surface `#1F1F26`, border `1px solid #2A2A32`, text `#F4F4F6`. On hover, border shifts to `#3E3E4A` with subtle background brightening.
- **Compact Action:** Height 36px, horizontal padding 14px, font size 13px (Plus Jakarta Sans SemiBold).

### Restaurant Cards
- Built on `#17171C` with a 1px border of `#2A2A32` and 16px radius.
- Imagery includes an integrated dark vignette gradient (`rgba(14, 14, 17, 0) 40%` to `rgba(14, 14, 17, 0.9) 100%`) overlaying dish photos for text legibility.
- Ratings badge pinned at the top-right: solid `#1F1F26` backing, warm amber star `#F5A524`, text `#F4F4F6` (bold, 12px).
- Hover effect transitions surface to `#1F1F26` and outer border to `#3E3E4A` over 200ms.

### Filter Chips & Tags
- **Default:** Background `#17171C`, border `1px solid #2A2A32`, text `#A1A1AA`, 12px font size, 12px radius.
- **Selected:** Background `rgba(226, 55, 68, 0.15)`, border `1px solid #E23744`, text `#FFFFFF`, subtle inner crimson shadow.

### Input Fields & Prompts
- Background `#17171C`, border `1px solid #2A2A32`, text `#F4F4F6`, radius 12px, padding `12px 16px`.
- Focus state switches border to `#E23744` with an immediate outer glow `0 0 0 3px rgba(226, 55, 68, 0.2)`. Placeholder text set to `#6B6B76`.

### AI Context & Status Banners
- Surface background using a 10% opacity tint of the respective status color against `#17171C`.
- Left structural anchor: solid 3px accent bar running edge-to-edge along the vertical axis.
- Radius: 12px, with padding `12px 16px`.
- Content: Pair a bold 13px status header with 13px secondary text describing AI recommendation parameters or fallback filters.

### Sliders (Budget & Distance)
- Track background: `#2A2A32`, height 4px, rounded-full.
- Fill color: `#E23744`.
- Thumb: 18px circle, `#FFFFFF` with a 2px `#E23744` border and `0 2px 8px rgba(0, 0, 0, 0.6)` drop shadow. Glows on drag.