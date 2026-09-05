## Summary

-

## Scope

- [ ] Documentation only
- [ ] Package CSS
- [ ] Optional ESM
- [ ] Catalog chrome
- [ ] Certification evidence
- [ ] Release or CI automation

## Public Contract Impact

- [ ] No public contract change
- [ ] Documented classes, selectors, `data-*`, or ARIA relationships changed
- [ ] Package exports or file list changed
- [ ] CSS load order or scoped `.moo-ui` behavior changed
- [ ] Bootstrap peer range or plugin ownership changed
- [ ] Optional Moo UI ESM lifecycle changed

## Verification

- [ ] `.venv/bin/python build.py`
- [ ] focused tier: `.venv/bin/python scripts/run-test-tier.py run quick`
- [ ] browser tier when relevant: `.venv/bin/python scripts/run-test-tier.py run browser-smoke`
- [ ] release tier before `dev` -> `main`, tags, or publish: `.venv/bin/python scripts/run-test-tier.py run release`
- [ ] `git diff --check`
- [ ] Browser/viewport checked:
- [ ] Keyboard/focus checked when interaction changed:
- [ ] Screen-reader or accessibility smoke checked when relevant:

## Notes

-
