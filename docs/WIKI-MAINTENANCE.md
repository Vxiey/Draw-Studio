# Wiki maintenance

The maintained Wiki pages live in `docs/wiki/`. Changes on main run the **Publish Image Draw Bot Wiki** workflow, which publishes those Markdown pages to the separate GitHub Wiki repository. Existing unrelated Wiki pages are preserved.

Use Wiki page links such as `(Getting-Started)` inside Wiki source. Use full GitHub URLs when linking back to the application repository. Keep current downloads, profile-specific setup and troubleshooting aligned with the released app.

Check the workflow result before claiming the Wiki has been published. The Wiki must already be initialized and the workflow token must have permission to push to its Git repository. If permissions change, the committed source pages remain available here while publication is blocked.
