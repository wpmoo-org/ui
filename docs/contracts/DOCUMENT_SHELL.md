# Document Shell Mode Contract (development candidate)

The app layout has three shell modes. `viewport` fills the viewport and scrolls
`main` between a pinned header and footer. `contained` bounds the shell inside a
host. `document` is for websites: the document is the scroll owner, `main` does
not scroll, and the footer follows the content.

In `document` mode the wrapper is at least `100svh` tall and grows with its
content. `main` keeps its flex growth, so the footer still meets the viewport
bottom on short pages. The header stays in normal document flow.

`document` mode requires `navigation="none"`; site navigation belongs in the
header or in a drawer overlay. Consumers should not place `main`-scoped scroll
utilities such as `scroll-fade-y` on `main` in this mode, because `main` is not
a scroll container. Overlay scrollbars and tables of contents use the document
as their scroll root.

Default output is unchanged for `viewport` and `contained`.
