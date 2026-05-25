# wedding-pages-invite

**Status:** TODO — not implemented yet.

Planned deliverable: the invite/keepsake for the junior wedding attendants —
flower girl, ring bearer, and bear bearer (the kids who walk the aisle and
carry the rings / petals / teddy).

Probably tri-fold like the bridesmaid manual, but with:

- Lighter / kid-friendly tone
- Outfit description for each child role (flower girl dress, ring bearer
  suit, bear bearer outfit)
- "Your job on the big day" simplified instructions
- A small keepsake page (photo placeholder for the kid)

## When implementing

Mirror the structure of `wedding-invite/`:

```
modules/wedding-pages-invite/
├── template/
├── inputs/
├── outputs/<run>/
├── content.yaml
├── layout.yaml
└── build.py
```

Add to `tui.py`'s active-modules list once `build.py` exists.

## Naming note

`pages` is the standard English wedding term for junior attendants
(flower girl + ring bearer + page boy). Picked over alternatives
(`wedding-kids-invite`, `wedding-junior-attendants`) for conciseness.
