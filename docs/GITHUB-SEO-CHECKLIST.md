# GitHub SEO checklist for Image Draw Bot

Use this checklist when publishing a release, editing the repository About box, or preparing a public link preview.

## Recommended GitHub About description

```text
Automatic image drawing bot for Windows. Converts pictures into mouse strokes, contours, fills and exact RGB colors for Microsoft Paint, Gartic Phone and Skribbl.io.
```

A shorter alternative for places with tight character limits:

```text
Windows image drawing bot for Microsoft Paint and drawing canvases: image-to-strokes, contours, fills, exact RGB colors and local processing.
```

## Recommended GitHub topics

Use lowercase GitHub topics that match real searches and technology names:

```text
image-drawing
drawing-bot
automatic-drawing
microsoft-paint
paint-automation
mouse-automation
image-to-strokes
image-processing
computer-vision
python
windows
customtkinter
tkinter
pillow
numpy
pyinstaller
opencl
cuda
gartic-phone
skribbl
```

## Social preview

Recommended file:

```text
assets/social-preview.png
```

The image should clearly show:

- the product name: Image Draw Bot
- the value proposition: automatic image drawing
- recognizable Paint / canvas / preview imagery
- no old product name
- no unreadable small text

GitHub repository settings do not automatically use repository files as the social preview. Upload the PNG manually in **Settings → General → Social preview** when changing the public repo card.

## README SEO rules

Keep the first screen of `README.md` optimized for both humans and search indexing:

- H1 should include the product name and the phrase `automatic image drawing bot`.
- The first bold sentence should mention Microsoft Paint, Gartic Phone, Skribbl.io, mouse strokes, contours, fills and exact RGB colors.
- Use descriptive image alt text, not generic words such as `screenshot`.
- Keep download links high in the README.
- Keep safety, privacy and unsigned-build warnings visible.
- Do not keyword-stuff repeated phrases into every heading.

## Release SEO rules

Release notes should include a short plain-English summary near the top:

```text
Image Draw Bot is a Windows automatic image drawing app that converts pictures into mouse strokes, contours, fill regions and exact RGB colors for Microsoft Paint and calibrated drawing canvases.
```

Also include the same artifact names users search for:

- Windows installer
- portable Windows ZIP
- SHA-256 checksums
- Microsoft Paint automation
- image-to-strokes rendering
- exact RGB color calibration

## Search terms to keep consistent

Use these terms consistently across README, release notes and public docs:

- Image Draw Bot
- automatic image drawing
- image drawing bot
- image-to-strokes
- Microsoft Paint automation
- Paint drawing bot
- safe mouse automation
- contour fill renderer
- exact RGB color calibration
- pixel accurate drawing
- local image processing
- Windows drawing automation

## Avoid

- old product names
- claims that the project is fully signed while releases are unsigned
- claims that every Paint/browser layout is verified
- claims that GitHub Actions artifacts are official releases
- saying AI image generation when the app performs deterministic local rendering
- calling the repo open-source unless a proper license file has been added
