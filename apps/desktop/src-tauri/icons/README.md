# App icons

Binary icon assets are intentionally **not** committed in this scaffold.

Generate them once before your first `npm run tauri build` using a single
1024×1024 PNG source (ideally the Miori presence orb on a near-black field):

```bash
# from apps/desktop/
npm run tauri icon path/to/miori-orb-1024.png
```

This produces every required size referenced in `tauri.conf.json`:

- `32x32.png`
- `128x128.png`
- `128x128@2x.png`
- `icon.icns` (macOS)
- `icon.ico` (Windows)

Until then, `npm run dev` (web) works without any icons.
