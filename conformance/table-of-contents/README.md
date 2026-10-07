# Table of Contents candidate

This independent HTML example consumes the generic Core component and runtime.
It uses no catalog chrome, chart selectors or Astro integration. It is a
development candidate, outside the existing conformance-kit certification.

The public Jinja macro is `table_of_contents(id, items, ...)`, with plain-text
`{ target_id, label }` items. `presentation="list"` is static anchor navigation;
`presentation="compact"` composes the existing Bootstrap Dropdown control and
an Overview/current-section indicator. Its menu spans the compact navigation
width. Empty items render nothing.

Optional `content_id` limits target resolution; its default is the nearest
resolved Moo owner. `scroll_root_id` selects an explicit ancestor scrolling
element; the default is document scrolling. Both presentations can consume
the same items with unique component IDs and complementary host visibility.
The host owns their position and sticky/header geometry.
The `--nested` host uses the existing Moo App layout without a navigation
sidebar. Header and compact bar remain above the scrolling main region;
ordinary aside content follows the article on narrow screens. The default
fixture uses document scrolling and leaves placement to the host.

The optional `TableOfContents` ESM class exposes `getInstance`,
`getOrCreateInstance`, `refresh` and `dispose`. Its `activationOffset` runtime
option is a finite nonnegative pixel value, default zero. Initialization is
explicit; loading the module does not scan the document. `refresh` re-resolves
native targets and can update the offset. `dispose` removes listeners, cancels
pending updates and restores original navigation/status state.

After runtime/build authorization, render from the repository root:

```sh
.venv/bin/python conformance/table-of-contents/render.py
```

The renderer also accepts `--theme dark`, `--direction rtl`, `--nested`,
`--short` and `--long-labels`. Serve the canonical repository root and open
`/conformance/table-of-contents/index.html`. The generated file is ignored.
Current source-mode initialization imports the canonical implementation;
package-build and immutable-artifact checks are separate acceptance steps.

The compact control requires Bootstrap's Dropdown runtime. Without JavaScript,
use the list presentation. Article bodies and ordinary aside blocks are not
duplicated; only the two navigation presentations share their section data.
