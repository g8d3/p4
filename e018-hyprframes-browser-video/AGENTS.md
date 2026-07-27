# e018 — HyperFrames Browser Video

Create a video about undetectable open-source browsers using [HyperFrames](https://github.com/heygen-com/hyperframes) (HTML video compositions).

HyperFrames CLI (`hyperframes`) is installed globally. It creates videos from HTML/CSS/JS compositions rendered via headless Chrome (Puppeteer).

## Topic

Undetectable open-source browsers — browsers that resist fingerprinting, automate browser detection bypass, or provide anti-detection features.

## Agents

- `ag-01/` — Research undetectable open-source browsers, write script + storyboard
- `ag-02/` — Create the HyperFrames video composition and render it

## Output

- `ag-01/output/script.md` — video script with narration text and scene descriptions
- `ag-02/output/FINAL.mp4` — rendered video
- `ag-02/output/metadata.json` — resource metadata

## HyperFrames CLI

```bash
hyperframes init <name>    # scaffold project
hyperframes preview        # preview in browser
hyperframes render -o out.mp4 --format mp4   # render
hyperframes catalog        # browse blocks/components
hyperframes add <name>     # add a block
hyperframes lint           # validate composition
hyperframes doctor         # check system
```

## Resolution

Mobile vertical: `--resolution portrait` (1080×1920).
