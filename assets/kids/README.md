# assets/kids — cover art slot for wedding-pages

Drop transparent-background PNGs of the cartoon couple here:

- `pajem.png`   — used on the Pajem manual cover
- `daminha.png` — used on the Daminha manual cover

The path is referenced from `modules/wedding-pages/content.yaml`
(`variants.<name>.cover.image`). If the file is missing, the build just skips
the illustration and prints a notice. The image lands in the lower half of the
front-cover panel, below the manual title; scaled to fit, aspect preserved.
