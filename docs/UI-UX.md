# UI/UX Documentation

## Design overview

The implemented UI is server-rendered Jinja with two shared shells:

- `auth_base.html`: split-panel authentication layout used by login, registration, Google profile completion, OTP, and reset pages.
- `base.html`: authenticated sidebar layout with admin/student themes, flash messages, dark-mode persistence, responsive navigation, and shared styles.

The public landing page and 404/500 pages are standalone. Visual conventions use Inter/Plus Jakarta Sans, blue/green/purple gradients, rounded cards, emoji icons, status badges, shadows, and CSS custom properties. Most CSS and JavaScript is embedded in templates.

## Pages and navigation

| Page | Audience | Primary UI |
| --- | --- | --- |
| Landing | Public | Hero, feature/role sections, sign-in/register calls to action |
| Login/register | Public | Email/password or profile fields, Google continuation, validation flashes |
| Forgot/verify/reset | Public flow | Email form, six-digit code with countdown/resend, new-password form |
| Dashboard | Both roles | Aggregate cards, recent placements, notification cards; role-aware messaging |
| Students | Admin | Search/filter table, pagination, add/edit/delete, CSV navigation |
| Bulk upload | Admin | Drag/drop-style CSV selector, expected columns, sample CSV download, progress animation |
| Companies | Both | Search/package filters and table; admin action controls |
| Placements | Both | Search/year/status filters and table; admin add/delete controls |
| Analytics | Admin | KPI cards and five Chart.js visualizations |
| Predictor | Both | Six-factor form, animated probability/result details, tips and tier suggestions |
| Profile | Primarily student | Identity/academic details, readiness presentation, placement history |
| Change password | Both | Current/new/confirmation form |
| Add/edit forms | Admin | Student, company, and placement fields |
| Errors | Public | Branded 404 and 500 recovery pages |

The sidebar shows dashboard and predictor to both roles. Admin navigation includes students, bulk upload, companies, placements, and analytics. Student navigation includes companies, “My Placements,” and profile. Despite the label “My Placements,” `/placements` currently renders all placement rows.

## Forms and interactions

Many forms are assembled and submitted by inline JavaScript rather than literal `<form>` markup. The script creates hidden CSRF inputs using Jinja’s token. Delete actions use HTML POST forms with confirmation prompts. Client interactions include table filtering, clear-filter actions, sidebar hamburger, theme toggle, password reveal, Enter-key submission on auth forms, upload file feedback, countdowns, stat animations, and chart tooltips.

Native input controls are used for dates, numbers, email, files, selects, checkboxes, and radio buttons. Server validation and flash messages remain authoritative.

## State handling

| State | Implemented behavior |
| --- | --- |
| Loading/submission | Several auth, predictor, analytics, and upload actions show button/progress animation; there is no global route-loading state |
| Empty | Tables/reports/predictor/profile sections provide feature-specific empty copy or initial blank state |
| Success/error | Server flash banners use category color/icon and auto-dismiss after four seconds; field-level inline errors are limited |
| Not found | Edit routes redirect with flash; dedicated 404 page covers unknown URLs |
| Server failure | Dedicated 500 page |
| Rate/CSRF/upload limit | Flash then redirect to a safe page |

## Responsive behavior

The shared shells define breakpoints around 1024, 768, and 480 pixels. The authenticated sidebar becomes a compact/mobile navigation controlled by a hamburger; cards/grids stack and spacing/type sizes reduce. Tables remain horizontally dense and rely on their containing layout/overflow behavior. Actual device/browser results were not interactively verified for this documentation task.

## Accessibility implementation

Implemented elements include semantic headings, navigation labeling on the landing page, labels associated with many inputs, native controls, `aria-hidden` on decorative SVGs, keyboard Enter handlers, focus styling in shared CSS, and responsive text/layout. Some accessibility gaps remain:

- several icon-only or emoji buttons lack an explicit accessible name;
- the sidebar hamburger has no `aria-label` or expanded state;
- flash messages do not declare a live region;
- JavaScript-created forms and click handlers are used heavily;
- chart data has no equivalent tabular/text alternative in the analytics page;
- color contrast, focus order, screen-reader behavior, and reduced-motion handling have not been audited or tested.

No conformance level should be claimed from repository evidence.

## Implemented versus not implemented

Implemented: responsive shells, role-specific navigation, persistent dark mode, client-side table filters, server flashes, empty/error pages, animated dashboard/predictor/chart presentation, and reusable shared CSS patterns.

Not implemented: SPA transitions, live updates, user-configurable dashboards, localization, notification center, field-level validation framework, offline behavior, automated accessibility testing, or a standalone design-system/component library.

