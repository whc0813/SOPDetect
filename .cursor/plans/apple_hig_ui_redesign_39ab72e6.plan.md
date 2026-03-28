---
name: Apple HIG UI Redesign
overview: Thoroughly restructure the UI of all three pages (Login, Admin, User) and their sub-pages/dialogs to strictly follow Apple Human Interface Guidelines, including extracting shared components and styles, adding dark mode, and improving layout consistency.
todos:
  - id: styles-foundation
    content: Create `src/styles/` with `variables.css` (Apple design tokens + dark mode), `base.css` (global resets), and `components.css` (shared utility classes). Import in `main.js`.
    status: completed
  - id: shared-components
    content: "Create shared components: `AppBlobs.vue`, `GroupedList.vue`, `SectionHeader.vue`, `StatusBadge.vue`, `GlassCard.vue` under `src/components/`."
    status: completed
  - id: app-vue-refactor
    content: "Refactor `App.vue`: move global styles to external files, add `<transition>` on `<router-view>` for page crossfade."
    status: completed
  - id: login-redesign
    content: "Redesign `Login.vue`: Apple ID style card, refined segmented control, leading icons in inputs, entry animation, dark mode compatible."
    status: completed
  - id: admin-redesign
    content: "Redesign `Admin.vue`: macOS sidebar pattern, grouped inset lists for tables, Apple sheet-style dialogs, refined stats view, dark mode compatible. Replace duplicated styles with shared classes."
    status: completed
  - id: user-redesign
    content: "Redesign `User.vue`: iOS-style navigation, refined task cards, list-style job/history views, improved execution sub-view, dark mode compatible. Replace duplicated styles with shared classes."
    status: completed
  - id: responsive-polish
    content: "Final responsive polish: sidebar collapse, table scroll, touch target audit, transition timing review across all views."
    status: completed
isProject: false
---

# Apple HIG UI Redesign Plan

## Current State Analysis

The project has 3 monolithic view files (~4300 lines of scoped CSS total) with heavily duplicated styles (blobs, badges, tables, dialogs, buttons appear in every file). There are no shared components under `src/components/`. The design already uses some Apple-inspired elements (SF Pro font, `#007AFF` accent, frosted glass) but inconsistently and with several HIG violations.

Key files:

- [bysj/src/App.vue](bysj/src/App.vue) - Global CSS tokens (~184 lines)
- [bysj/src/views/Login.vue](bysj/src/views/Login.vue) - Auth page (~538 lines)
- [bysj/src/views/Admin.vue](bysj/src/views/Admin.vue) - Admin dashboard (~1977 lines)
- [bysj/src/views/User.vue](bysj/src/views/User.vue) - User dashboard (~1827 lines)

---

## 1. Design System Foundation

### 1.1 Shared Style Layer (`src/styles/`)

Create a `src/styles/` directory with extracted global styles to eliminate the ~1200 lines of duplicated CSS:

- `**variables.css**` - Design tokens following Apple's semantic color system, including **dark mode** support via `@media (prefers-color-scheme: dark)`. Tokens cover:
  - Label colors (primary, secondary, tertiary, quaternary)
  - System backgrounds (primary, secondary, tertiary, grouped variants)
  - Fill colors (primary through quaternary)
  - Separator colors (opaque and non-opaque)
  - System tint colors (blue, green, indigo, orange, pink, purple, red, teal, yellow)
  - Type scale following Apple's ramp: Large Title (34px/700), Title 1 (28px/700), Title 2 (22px/700), Title 3 (20px/600), Headline (17px/600), Body (17px/400), Callout (16px/400), Subheadline (15px/400), Footnote (13px/400), Caption 1 (12px/400), Caption 2 (11px/400)
  - Spacing on an 8pt grid
  - Apple's material backgrounds (ultra-thin, thin, regular, thick, ultra-thick)
  - Motion tokens (spring curves, durations)
- `**base.css`** - Reset, `html/body`, global Element Plus overrides (dialog, message box)
- `**components.css`** - Shared utility classes: `.badge`, `.table-card`, `.data-table`, `.pill-btn`, `.text-btn`, `.detail-box`, `.blob`, `.stat-card` etc. currently duplicated across views

### 1.2 Dark Mode

Add full dark mode support through CSS custom properties. All three views will automatically adapt. Key dark mode values following Apple HIG:

```css
@media (prefers-color-scheme: dark) {
  :root {
    --bg-base: #000000;
    --surface: #1c1c1e;
    --surface-strong: #2c2c2e;
    --text-main: #ffffff;
    --text-soft: rgba(235, 235, 245, 0.6);
    --accent: #0a84ff; /* Apple blue shifts in dark mode */
    /* ... */
  }
}
```

---

## 2. Shared Components (`src/components/`)

Extract these reusable components to reduce duplication and enforce visual consistency:


| Component           | Replaces                                                                                  | Used In            |
| ------------------- | ----------------------------------------------------------------------------------------- | ------------------ |
| `AppBlobs.vue`      | Ambient background blobs (identical in all 3 views)                                       | Login, Admin, User |
| `GroupedList.vue`   | Native `<table>` with Apple grouped-list styling (rounded sections, inset separators)     | Admin, User        |
| `SectionHeader.vue` | `.section-head`, `.page-header` patterns                                                  | Admin, User        |
| `StatusBadge.vue`   | `.badge` + all variants (success/danger/warning/info/default)                             | Admin, User        |
| `GlassCard.vue`     | `.table-card`, `.stat-card`, `.step-container`, `.job-status-card` glass material pattern | Admin, User        |


---

## 3. Page-by-Page Redesign

### 3.1 Login.vue - Apple ID Style

Current design is already close. Key refinements:

- **Card**: Reduce max-width to 380px, increase corner radius to 30px (closer to Apple ID web login)
- **App icon**: Add subtle background glow animation on load (like Apple device setup)
- **Segmented control**: Use the Apple iOS 16+ segmented control pattern with pill-shaped active indicator and spring animation
- **Form fields**: Keep filled-style inputs, add SF Symbols-style icons (lock, person) as leading icons inside inputs, increase field gap to 16px
- **CTA button**: Use Apple's system blue with the exact gradient `linear-gradient(180deg, #0A84FF, #007AFF)` and pressed state
- **Entry animation**: Fade-in + slight scale-up on mount (0.96 -> 1.0, 400ms spring)
- **Footer hint**: Lighter, use Caption 1 size (12px)

### 3.2 Admin.vue - macOS Sidebar Layout

Follow the macOS Ventura System Settings / Finder pattern:

- **Sidebar**:
  - Width stays at 240px, use Apple's ultra-thick material background
  - Navigation items: 36px height, 10px corner radius, SF-style rounded-rect icon badges (already present, refine sizing)
  - Active state: Use Apple's selection blue with `rgba(0, 122, 255, 0.15)` background instead of gray
  - Add a collapse button for responsive (hamburger menu on mobile)
  - User card at bottom: Use the macOS account switcher pattern with avatar + chevron
- **Main content area**:
  - **Header bar**: Reduce to 64px height, left-align title with Apple Title 1 size (28px), move action buttons to trailing edge
  - **SOP Management tab**: Replace raw `<table>` with Apple-style **grouped inset list** (white background sections with rounded corners, 16px inset padding, separator lines that don't touch edges)
  - **User Management tab**: Same grouped list treatment
  - **Statistics tab**: 
    - Stat cards: Use 2x2 grid (not 4 columns), larger numbers (48px), add SF Symbols icons in each card
    - SOP stats table: Grouped list style
    - History filter toolbar: Use Apple-style search bar + filter chips, move segmented filter into a horizontal scroll pill bar
    - History table: Grouped list style
- **Dialogs (5 total)**:
  - Use Apple sheet pattern: slide down from top with spring animation
  - Form fields: Apple grouped-form style (fields inside rounded sections with separators between them, like iOS Settings forms)
  - Footer buttons: Right-aligned, primary button uses filled blue, cancel uses text-only style

### 3.3 User.vue - iOS-Inspired Single Page

Follow iPad/iOS app patterns:

- **Top navigation bar**:
  - 48px height, center the brand name, avatar + user info trailing
  - Use Apple's `regularmaterial` background
- **Tab bar / Segmented control**:
  - Use a more prominent segmented control centered below the nav bar
  - Consider using Apple-style **scope bar** pattern (attached to the navigation bar)
- **Tasks tab (home)**:
  - Hero greeting: Use Apple's Large Title (34px) style, remove the extra-large 44px
  - Task cards: Use Apple's **grouped inset list rows** instead of grid cards for simpler scanning, or keep cards but add a subtle left-edge color accent per card
  - Empty state: Use SF Symbols-style illustration, not emoji
- **Evaluation Jobs tab**:
  - Replace table with a **list view** (each row is a card-like list item with status badge, progress bar, and chevron disclosure)
  - Show job status using Apple-style inline progress indicators
- **History tab**:
  - Same list/grouped-table treatment
- **SOP Execution sub-view**:
  - Back button: Use Apple's `< Back` chevron pattern (blue chevron + text, 44px touch target)
  - Timeline: Keep the timeline but refine dot sizes to 24px, use `SF Mono` for step numbers
  - Upload area: Use Apple's document picker pattern (less decorated, cleaner drop zone)
  - Result card: Use Apple notification/alert card style
- **History detail dialog**: Grouped form sections, same sheet treatment as Admin dialogs

---

## 4. Transition and Motion

- **Page transitions**: Add `<transition>` wrapper to `<router-view>` in `App.vue` with a subtle crossfade (200ms)
- **Tab transitions**: Slide left/right when switching tabs within User.vue
- **List item animations**: Staggered fade-in for table rows and cards on mount
- **Dialog animations**: Spring-based slide-down entry, fade+scale exit
- **Hover states**: All interactive elements use Apple's standard 100ms ease feedback
- **Active/press states**: Scale(0.97) press feedback on all buttons and cards (already partially present)

---

## 5. Responsive Design Improvements

- **Admin sidebar**: Collapses to a hamburger overlay on screens < 768px (use a slide-over panel pattern like iPadOS)
- **Statistics grid**: 2 columns on tablet, 1 column on phone
- **Tables**: Horizontal scroll with sticky first column on narrow screens, or collapse to card-based list view
- **User tasks**: Single column card layout on mobile
- **Touch targets**: Ensure all interactive elements are >= 44px (Apple's minimum)

---

## Implementation Order

Work bottom-up: shared layer first, then components, then refactor each view.