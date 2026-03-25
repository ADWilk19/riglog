# RigLog Brand Kit

## Recommended repo structure

```text
riglog/
├─ app/
├─ assets/
│  ├─ branding/
│  │  ├─ logo_full.png
│  │  ├─ logo_full_dark.png
│  │  ├─ icon_1024.png
│  │  ├─ icon.icns
│  │  ├─ logo_concept_initial_rl_drop.png
│  │  ├─ logo_vascular_drop.png
│  │  ├─ logo_full_detailed.png
│  │  └─ logo_system_full_and_simplified.png
├─ docs/
│  └─ brand/
│     └─ BRANDKIT.md
```

## Best place to put the brand kit

The best place for the written brand kit is:

- `docs/brand/BRANDKIT.md`

That keeps the guidance separate from runtime code and makes it easy to maintain.

The best place for the actual logo/image assets is:

- `assets/branding/`

That keeps all visual assets together and makes packaging easier later.

## Logo set currently exported

1. `logo_concept_initial_rl_drop.png`
   - First combined RL + blood drop concept.

2. `logo_vascular_drop.png`
   - Vascular blood drop exploration without letters.

3. `logo_full_detailed.png`
   - Detailed vascular drop with RL overlay.

4. `logo_system_full_and_simplified.png`
   - Side-by-side full and simplified logo system.

## Final polish recommendations

- Round the inner corners of the RL monogram.
- Use off-white lettering: `#F5F5F5`.
- Slightly darken the centre red behind the letters for separation.
- Reduce graph opacity to roughly 70–80%.
- Add a darker outer red stroke to the drop for contrast on macOS backgrounds.
- Keep a simplified icon variant specifically for dock-scale rendering.

## Core palette

- Primary Red: `#C62828`
- Deep Red: `#8E0000`
- Light Red: `#EF5350`
- Off-white: `#F5F5F5`
- Background Dark: `#121212`
- Surface Dark: `#1E1E1E`
- Border: `#2A2A2A`

## Recommended usage

- Full logo: splash screen, README, GitHub, future landing page.
- Simplified icon: macOS dock, app icon, toolbar, packaged app bundle.
