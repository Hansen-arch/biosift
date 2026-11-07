# BioSift DESIGN.md, direction for UI work

> Reading this as: a biodiversity data-quality workbench for researchers
> and GBIF node staff, in a light scholarly ledger style (a methods
> journal on paper), dial ENERGY 1 / RHYTHM 2 / MOTION 1.
> Direction chosen by the project owner 2026-10-21 ("light scholarly
> look"), applied with the antislop filter (`antislop.md` + `skills/`).

## Identity

BioSift looks like the paperwork around the data, not like a SaaS that
sells something: a specimen label, a survey ledger, a methods journal
page. Flat ink on warm paper, hairline rules, tabular numerals, mono for
machine strings (commands, schema versions, API recipes). No glow, no
gradient wash, no glass. If the logo and name were swapped out, the
ledger lines, the honest caveats and the rerunnable exports should
still read as BioSift.

## Palette (2 core + 1 accent, R-29)

- Paper background `#F4F1E8`, card `#FBF9F2`, sidebar/sunken
  `#EDE9DC`, hairline `#D6CFBC`, rule `#B9B09A`: warm paper because
  this is scholarly reference material, read side by side with printed
  tables and manuscripts, not a dashboard watched in the dark (R-21;
  the earlier dark theme was chosen for long map sessions and was
  replaced on the owner's call).
- Ink `#232019` text, `#5C5647` body, `#6E6653` small labels (all pass
  WCAG AA on card; verified with `skills/antislop-human/contrast-check.py`,
  R-25).
- One accent, deep emerald `#136F4E`: reserved for the primary action,
  pass/health states, and the lead-card top rule. Amber `#75530F` and
  red `#A2382B` carry warn/fail only (R-29). Data colours (`utils/theme.D`:
  `#1E7A54`, `#C9922B`, `#C2402F`, `#C97B23`) are vivid state encoding
  for maps and chart series, never UI text.
- IUCN chips keep the official IUCN category colours: they are a
  standard's data, not our palette.

## Typography (reason, R-31)

- UI text: system stack, tabular numerals. Reason: analysts compare
  numbers across rows; webfont fetching adds weight for zero benefit.
- Display (hero, page titles, verdict numbers): Georgia serif. Reason:
  editorial voice of a journal methods section, distinct from the data
  sans.
- Mono: machine strings only (commands, schema IDs, BDQ test IDs, the
  field-log kicker). Reason: marks what to copy or cite, never body
  copy (R-06).

## Layout (reason, R-31)

- Lead cards carry a 3px accent top rule; depth features do not. Reason:
  the three entry points (audit, benchmark, your own data) outrank the
  rest; the rule encodes hierarchy, which is a signal, not decoration.
- Audiences render as ledger lines, run steps as shell commands. Reason:
  reference rows and copy-paste commands are not product pillars, so
  they are not cards (R-05, R-14).
- Hero facts render as ledger items between rules, not pills. Reason:
  sample size, runtime and licence are provenance statements, not
  status; a pill is reserved for state (R-09).
- Radius scale is near-square (4px, 3px for segmented controls) because
  a printed form is near-square; the 999px pill is reserved for status
  badges because a pill marks state (R-11). Surfaces are flat: hairlines
  carry structure, so there are no shadows except the map popup, which
  genuinely floats above the map (R-12).
- Copy rule: every number ships with its source or sample size; no
  claim without evidence (C-5, R-17, R-36). Em dash never appears in
  rendered copy (R-02); missing values read `n/a`.

## Dials

ENERGY 1 (quiet instrument) / RHYTHM 2 (ledger lines break the card
grid, sections otherwise consistent) / MOTION 1 (hover states only;
maps cluster and pop per MapLibre patterns; no loops, no pulses).

## Liveliness levers

- Focal point per screen: the verdict (health score, SDM gate). The
  verdict number is the only serif-display value on a results screen.
- Identity motif: the field-log kicker (`field log · v3.4 · …`) ruled
  off above the hero title, and ledger rules repeated on every page.
- Honest caveats inline (lion fails on uncertainty, hulls overstate
  range): specificity is the anti-slop device.
