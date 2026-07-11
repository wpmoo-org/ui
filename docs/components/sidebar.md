# Sidebar

`moo_ui.sidebar_*` templates provide a Shadcn-inspired compound Sidebar for
Odoo portal and website surfaces. The caller owns labels, routes, icons, menu
data, active state, and any domain-specific content.

```xml
<t t-call="moo_ui.sidebar_layout">
    <t t-set="sidebar_layout_class" t-value="'my_shell'"/>
    <t t-set="sidebar_compact" t-value="False"/>
    <t t-set="sidebar_storage_key" t-value="'my.sidebar.compact'"/>
    <t t-set="sidebar_cookie_key" t-value="'my_sidebar_compact'"/>
    <t t-call="moo_ui.sidebar">
        <t t-set="sidebar_id" t-value="'my_sidebar'"/>
        <t t-set="sidebar_label" t-value="'Navigation'"/>
        <t t-call="moo_ui.sidebar_header">
            <a href="/">Brand</a>
        </t>
        <t t-call="moo_ui.sidebar_content">
            <nav>Links</nav>
        </t>
        <t t-call="moo_ui.sidebar_footer">
            <button type="button">Account</button>
        </t>
    </t>
    <t t-call="moo_ui.sidebar_inset">
        <t t-call="moo_ui.sidebar_trigger">
            <t t-call="moo_ui.icon">
                <t t-set="icon_name" t-value="'panel-left'"/>
            </t>
        </t>
        <t t-out="0"/>
    </t>
</t>
```

Mobile open and close behavior is Bootstrap Offcanvas. Desktop compact state is
owned by the `moo_ui.sidebar` public interaction and persisted through the
configured storage and cookie keys.

Header, content, and footer are QWeb body slots. Consumers may add classes, but
`moo_ui` must not depend on a consumer addon.
