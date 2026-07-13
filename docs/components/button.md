# Button

Button styles regular Bootstrap buttons inside a `.moo-ui` scope. HTML users
write Bootstrap classes directly; Odoo users may use the QWeb adapter.

## API

| Prop | Values | Default |
| --- | --- | --- |
| `variant` | `default`, `outline`, `ghost`, `destructive`, `secondary`, `link` | `default` |
| `size` | `default`, `xs`, `sm`, `lg`, `icon`, `icon-xs`, `icon-sm`, `icon-lg` | `default` |
| `type` | `button`, `submit`, `reset` | `button` |
| `disabled` | boolean | `False` |
| `button_class` | string | empty |
| `button_attrs` | dict | `{}` |

## HTML

```html
<div class="moo-ui">
  <button type="button" class="btn btn-outline-secondary btn-xs">
  Review
  </button>
</div>
```

## QWeb

```xml
<t t-call="moo_ui.button" variant.f="outline" size.f="xs">
    Review
</t>
```

Use a real `<button>` for actions. Use a real `<a>` with the documented classes
for navigation links. Icon-only buttons need an accessible name such as
`aria-label`.

References checked on 2026-07-13:

- https://ui.shadcn.com/docs/components/base/button
- https://getbootstrap.com/docs/5.3/components/buttons/
