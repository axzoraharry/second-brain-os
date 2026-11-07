# repo-checks — Control Room · UI/UX Redesign Prompt

A detailed visual prompt for rebuilding `repo-checks` as a state-of-the-art
frontend experience. Feed this to a design system, a frontend generator (v0 /
Bolt / Lovable / Claude Artifacts), or a human designer. It is written to be
**buildable**, not aspirational: every effect maps to a real CSS / JS / WebGL
capability.

---

## 1. Concept & story

**"The Control Room."** This is not a table of repositories — it is a live
mission console for an AI engineer's fleet of agents, repos, and local clones.
The user walks in and *sees the state of their entire system* in one glance:
what is healthy, what is unlicensed, what has been abandoned, and whether the
checks themselves are still fresh.

Mood: **dark glass orbital** — deep space navy, thin luminous borders, aurora
light bleeding behind panels, a sense of calm authority. Nothing blinks
gratuitously; every animation communicates a *transition of state*.

---

## 2. Layout & information architecture

```
┌───────────────────────────────────────────────────────────────┐
│  HEADER   live clock · engine · mode · "last sync" · pulse    │
├───────────────────────────────────────────────────────────────┤
│  HERO     4 stat tiles (total / ok / at-risk / abandoned)     │
│           count-up numbers + verdict donut (SVG)              │
├───────────────────────────────────────────────────────────────┤
│  AUTOMATION PIPELINE                                          │
│  Discover → Fetch → Check → Verdict → Log → Ship              │
│  (6 nodes, animated data-flow connectors)                     │
├───────────────────────────────────────────────────────────────┤
│  TOOLBAR   search · verdict filter chips · sort · grid/table  │
├───────────────────────────────────────────────────────────────┤
│  REPO GRID  3D-tilt cards (or table rows)                     │
│  each: verdict badge · licence · staleness ring · CI/README   │
│  dots · local-sync · check-age                                │
└───────────────────────────────────────────────────────────────┘
```

Responsive: grid = 3 columns → 2 → 1; toolbar collapses to an icon row;
pipeline becomes vertical on <640 px.

---

## 3. Design tokens

| token | value |
|---|---|
| background | `#05070d` → radial aurora (indigo `#312e81`, violet `#6d28d9`, cyan `#0891b2`) at 15–25 % opacity, slowly drifting |
| glass panel | `rgba(255,255,255,0.04)` + `backdrop-filter: blur(18px)` + 1 px `rgba(255,255,255,0.08)` border |
| text primary / secondary | `#e8edf6` / `#8b96ad` |
| mono (numbers, IDs) | `ui-monospace, SFMono-Regular, Menlo` |
| radius | cards 18 px, chips 999 px, panels 22 px |
| shadow | `0 20px 60px -30px rgba(0,0,0,0.9)` |

Verdict colour language (semantic, accessible on dark):

| verdict | colour |
|---|---|
| ok | `#34d399` |
| warn | `#fbbf24` |
| unlicensed / fail | `#fb7185` / `#f87171` |
| unknown | `#a78bfa` |
| abandoned / archived / disabled | `#64748b` |

Staleness ring: fresh `#34d399` → aging `#fbbf24` → stale `#fb923c` →
abandoned `#f87171` → unknown `#64748b`.

---

## 4. The "4D" transition system

**4D = 3 spatial axes + time.** Every transition declares (a) a *spatial path*
in perspective and (b) a *temporal curve*, and (c) a *stagger* relative to its
siblings. 3D alone is decoration; 4D is 3D choreographed through time so the
eye is led from cause → effect.

**a) Spatial (the 3 axes)**
- Entrances rise and settle: `translate3d(0, 24px, -40px) → identity` under
  `perspective: 1200px`, with `opacity 0 → 1`.
- Cards tilt in 3D on pointer hover (max ±7° rotateX/rotateY, `translateZ`
  lift 12 px), with a specular glare that tracks the cursor. Revert with a
  spring, never a hard snap.
- Table rows slide on the Z axis by depth (`translateZ`), giving a subtle
  parallax when the whole list is scrolled.

**b) Temporal (the 4th axis — the curves)**
- Default easing: spring `cubic-bezier(0.16, 1, 0.3, 1)` (~200 ms).
- Emphasis (verdict changes, filter reorder): overshoot `cubic-bezier(0.34, 1.56, 0.64, 1)` (~320 ms) — it must *settle*, not bounce indefinitely.
- Entrance stagger: `animation-delay = index × 24 ms`, capped at ~480 ms.
- Numbers count up over 800 ms with the same spring.

**c) Choreography rules**
- Filtering reorders with **FLIP** (First/Last/Invert/Play): measure, invert
  transforms, play — so cards *fly* to their new positions rather than
  teleporting.
- State changes use the **View Transitions API** where available, falling back
  to FLIP.
- One motion on screen at a time unless it is a coordinated stagger.

---

## 5. Motion inventory (state-of-the-art, but purposeful)

| interaction | effect |
|---|---|
| page load | aurora fades in (1200 ms) → header drops → stats count up → cards stagger in |
| hover (card) | 3D tilt + glare + lift + border glow in verdict colour |
| filter chip select | chip fills with verdict colour, cards FLIP to new order, non-matching cards scale to 0.96 / fade to 30 % |
| sort | same FLIP, with a brief "reorder wave" (one axis at a time) |
| grid ↔ table toggle | cross-fade + 3D rotateX(90°)→0 flip between modes |
| verdict change (live) | badge pulses once, card border flashes the new colour |
| automation pipeline | a "data packet" dot travels node → node; connectors draw themselves (stroke-dashoffset → 0); a node lights green on completion |
| stale check warning | the check-age number turns amber > 24 h, rose > 7 d, with a slow breathing pulse |
| reduced motion | all of the above collapse to opacity-only fades ≤ 150 ms |

---

## 6. The automation workflow (visual centrepiece)

A horizontal (vertical on mobile) pipeline of **six nodes** — the exact steps
`repo_checks.py` performs:

```
Discover ──► Fetch ──► Check ──► Verdict ──► Log ──► Ship
 (API)     (readme)  (7 rules)  (ok/fail) (json)  (commit)
```

- Each node: icon + label + a status ring that is `done` (filled green),
  `running` (spinning arc), or `pending` (dim).
- Between nodes: a connector line that **draws itself** on load (SVG
  `stroke-dasharray`/`stroke-dashoffset` animation), then a soft "packet" dot
  flows along it in a loop.
- The pipeline reads the real report: `summary` drives node colours, and
  `mode` ("dry-run" vs "apply") is shown as a badge — dry-run renders the
  pipeline in amber "preview" state, apply in green "live" state.
- This is the "seamless automation" story: the user sees the engine's own
  lifecycle, not just its output.

---

## 7. Component specs

**Stat tile** — glass card, big mono number (count-up), label, a tiny sparkline
or delta. The "at-risk" tile (unlicensed + abandoned) uses the rose accent and
is the first thing the eye lands on.

**Verdict donut** — SVG ring, one arc per verdict, stroke width ~10, rounded
caps, `stroke-dasharray` percentages, hover reveals the count in a tooltip.
Animated: arcs sweep in from 12 o'clock.

**Repo card** —
- Top row: repo name (mono) + verdict badge (pill).
- Staleness ring (24 px SVG) showing days/365; colour = staleness status.
- Meta row: licence chip (MIT = emerald, none = rose, NOASSERTION = violet "?");
  README and CI as three-state dots (pass=emerald, fail=rose, unknown=violet).
- Local-sync line: `in sync` / `behind N` / `unpushed` / `dirty` / `—`.
- Check-age: "checked 0.1 d ago" — turns amber/rose as it ages (staleness of
  the *check itself*).
- Click → expand (FLIP) to reveal full check detail JSON.

**Search** — filters as you type with a 60 ms debounce; highlight matched
characters.

**Filter chips** — one per verdict + "all", showing live counts; selecting
multiple ORs them.

---

## 8. Accessibility & performance

- Contrast ≥ 4.5:1 for all text on the dark base.
- `prefers-reduced-motion: reduce` disables tilt, FLIP, count-up, and pipeline
  loop; fades only.
- All animation is `transform` + `opacity` (GPU-composited); no `left/top/width`
  animation. Aurora uses `will-change: transform` and pauses off-screen
  (`IntersectionObserver`).
- Keyboard: cards are focusable, chips are toggle buttons, table has row focus.
- Numbers use tabular-nums so count-ups don't jitter the layout.

---

## 9. Tech stack

- **Vanilla HTML/CSS/JS** (no framework) so the dashboard is a single file that
  works from `file://` and behind a static server alike.
- CSS custom properties for the token system; SVG for donut/rings/connectors;
  CSS 3D transforms + `perspective` for the 4D layer; View Transitions with
  FLIP fallback.
- Data source: `data/repo-checks.json` (fetched; graceful fallback to an
  embedded sample when offline).

---

## 10. Definition of done

1. Loads in < 1 s on a mid-range phone; 60 fps during tilt and FLIP.
2. Every verdict and staleness state is visually distinct without colour alone
   (icon + label + colour).
3. Reduced-motion users lose nothing functionally.
4. The automation pipeline reflects the *real* run state, not a mock.
5. Single file, no build step, no external CDN.
