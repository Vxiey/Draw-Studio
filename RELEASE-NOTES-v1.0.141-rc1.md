# Draw Studio 1.0.141-rc1

## Microsoft Paint automatic custom colors

- Fixes Auto Paint preparation on current Windows 11 Paint/XAML controls that expose a named UI control but no `InvokePattern`/`SelectionItemPattern`.
- `Edit colors` is now discovered across current English/Swedish aliases and Button/MenuItem/Custom UI Automation variants.
- Control activation uses bounded fallbacks: Invoke, SelectionItem, Toggle, ExpandCollapse, LegacyIAccessible, then focused Enter on the already re-resolved UI element. No guessed canvas coordinate is clicked.
- Auto preparation captures and saves the `Edit colors` opener plus numeric Red/Green/Blue fields and OK button for the Microsoft Paint profile.
- During rendering Draw Studio can open `Edit colors`, type the image-derived RGB values automatically, confirm them, verify the rendered color, and persist verified RGB entries in the existing profile-isolated color cache.
- Reused verified colors remain bound to the calibration fingerprint/workflow so stale Paint layouts cannot silently reuse old coordinates.

## Regression coverage

- Adds current English `Edit colors` automatic-calibration coverage.
- Adds regression coverage for Paint controls without Invoke/SelectionItem support.
- Full Windows/Linux CI and DrawBot Windows self-test remain required before merge/release.
