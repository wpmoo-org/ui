# Page available-width grid

Moo Page marks its main-content rail with `data-page-container`. The rail
is the named `moo-page` CSS inline-size query container, so its content width
is measured after any Bootstrap `container-*` cap and padding. The optional
Sidebar's geometry can change this width without JavaScript or a reload.

Use Bootstrap's row, gutters, and one base `col-N` class per direct item. Opt
in with `data-layout="page-grid"` on the row, then use `data-page-col-sm`,
`-md`, `-lg`, `-xl`, or `-xxl` on direct items with values 1–12. The
breakpoints are 576, 768, 992, 1200, and 1400 CSS pixels of **rail content**.
Omitted breakpoint values inherit the last active width. Viewport-responsive
`col-sm-*`/`col-lg-*` classes must not be combined with page-column attributes
on one item. Ordinary Bootstrap grids remain viewport-based and unchanged.

```html
<div class="container-fluid" data-page-container>
  <div class="row" data-layout="page-grid">
    <div class="col-12" data-page-col-lg="3">Navigation</div>
    <div class="col-12" data-page-col-lg="9">One content body</div>
  </div>
</div>
```

Any descendant can use `data-page-show-from="lg"` or
`data-page-hide-from="lg"` to switch companion navigation at the same rail
threshold. The compact branch is visible when container queries are not
supported. Keep forms and IDs in one content body; duplicate only genuinely
alternate navigation. A capped rail (for example `container-xl`) might never
reach `xl`/`xxl` page-query thresholds even on a very wide viewport.
