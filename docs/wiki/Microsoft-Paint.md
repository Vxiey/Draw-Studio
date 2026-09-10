# Microsoft Paint setup

## Automatic workflow

Open one Paint window with a blank, fully visible canvas. Select **Microsoft Paint**, load an image and press **Prepare Paint & draw**. The app prepares the canvas, Pencil size, palette and RGB controls before drawing. Tests and previews are optional.

Keep Paint and Image Draw Bot at the same Windows privilege level, normally without administrator rights. Preparation can stop when multiple Paint windows, covered controls or ambiguous fields make detection unreliable.

## Custom color palette for picture

With an image loaded, this action analyzes important colors, prepares Edit colors R/G/B controls when needed and enters image-specific custom colors. It operates Paint controls: leave the mouse alone. From rc6, this action calibrates only RGB controls, waits for the numeric fields before typing and verifies dialog closure between colors. RGB calibration is saved separately from canvas detection. Preloading colors does not guarantee every later mark is correct; runtime checks still apply.

## When setup fails

Read the status message. Make the full blank canvas and toolbar visible, close extra Paint windows and check the selected profile. Changes to zoom, scaling and tool layout can require recalibration. Manual calibration is available, but the automatic Start path still requires successful fresh preparation.

Automatic accessible-control matching covers Swedish and English names in supported modern Paint layouts. Other versions or layouts may need manual setup. Passing automated tests does not guarantee compatibility with every Paint installation.

[Detailed automatic preparation and validation scope](https://github.com/Vxiey/Image-Draw-Bot/blob/main/docs/PAINT-AUTOMATIC-PREPARATION.md) · [Troubleshooting](Troubleshooting)
