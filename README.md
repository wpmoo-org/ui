# Moo UI

Reusable Odoo 19 UI primitives by WPMoo.

`moo_ui` provides source-owned QWeb, Bootstrap, SCSS, and Odoo public-interaction
components. It contains no business models, portal routes, user roles, or
project-specific workflows.

Small primitives live together in `moo_ui`. Features with substantial optional
assets or dependencies receive a separate addon only after a real consumer
requires them.

Component QWeb templates live under `moo_ui/components/<component>.xml`.
Component browser assets live under `moo_ui/static/src/components/<component>/`
so Odoo's asset loader can still resolve them from `static/`.
