# App Icons

Tauri expects the following icon files in this directory. Generate them from a
single 1024×1024 PNG master using the Tauri CLI:

```bash
npm --prefix ../frontend run tauri icon path/to/icon-1024.png
```

Expected files (produced by the command above):

- `32x32.png`
- `128x128.png`
- `128x128@2x.png`
- `icon.icns`  (macOS)
- `icon.ico`   (Windows)

These are referenced from `../tauri.conf.json` under `bundle.icon`. Until
they are generated the release build will fail — see the README "Icons" section
for the source master image.
