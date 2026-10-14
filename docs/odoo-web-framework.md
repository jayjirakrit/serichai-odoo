# Odoo 19.0 Web Framework: OWL and the Web Client

Architecture reference for the Serichai ERP frontend. It is the client-side
companion to [`odoo-framework.md`](odoo-framework.md), which covers the server.
It is based on a scan of the vendored core in `odoo/addons/web/` (the `web`
addon) and the server pieces that feed it. Paths are relative to
`odoo/addons/web/static/src/` unless they start with `odoo/` or `addons/`.
Line numbers refer to that source. The code was read, not executed.

Contents

1. Layers
2. Assets and the JS module system
3. OWL as Odoo uses it
4. Boot sequence
5. Registries
6. Services
7. Action manager and router
8. Views
9. Data model (RelationalModel)
10. Fields
11. Core UI components
12. Patching and extension
13. Errors and debug
14. Testing (Hoot)
15. Bundled third-party libraries
16. Implications for this repo

---

## 1. Layers

```
 Server bootstrap     addons/web/controllers/home.py   /odoo → web.webclient_bootstrap template
                                                       injects odoo.__session_info__ + <t t-call-assets="web.assets_web">
 Asset pipeline       odoo/addons/base/models/ir_asset.py, assetsbundle.py, odoo/tools/js_transpiler.py
 Module loader        module_loader.js                 odoo.define / ES-module shim, "@web/..." names
 UI library           lib/owl/owl.js (OWL 2.8.2)       Component, App, reactivity, QWeb→JS compiler
 Env + services       env.js                           env = { bus, services, debug, isSmall, … }
 Registries           core/registry.js                 services, views, fields, actions, systray, …
 Web client shell     webclient/webclient.js           NavBar, ActionContainer, MainComponentsContainer
 Action manager       webclient/actions/action_service.js  ir.actions.* → controllers + breadcrumbs
 Views                views/view.js + views/<type>/    Controller / Renderer / ArchParser / Model
 Data layer           model/relational_model/          Record, StaticList, DynamicLists → ORM RPCs
 Fields               views/fields/                    ~100 widgets registered in "fields"
 Transport            core/network/rpc.js, core/orm_service.js  JSON-RPC to /web/dataset/call_kw
```

Odoo builds the frontend the same way it builds the backend. The core is
small, and nearly every feature (services, views, fields, systray items,
error handlers) is an entry in a registry that other addons can add to or
override.

## 2. Assets and the JS module system

**Bundles** are declared in each addon's `__manifest__.py` under `assets`.
The `web` addon (`addons/web/__manifest__.py`) defines the main ones:

| Bundle | Line | Purpose |
|---|---|---|
| `web._assets_core` | 362 | module loader, luxon, `owl.js`, `odoo_module.js`, `env.js`, `session.js`, all of `core/**` |
| `web.assets_backend` | 49 | the backend client: includes `_assets_core`, bootstrap, SCSS, views, webclient. **Custom addons append here.** |
| `web.assets_web` | 147 | `assets_backend` plus `main.js` and `start.js`; this is the bundle the bootstrap page loads |
| `web.assets_backend_lazy` | 133 | graph and pivot views, loaded on demand (see §8) |
| `web.assets_frontend` | 164 | website and portal (public) pages |
| `web.report_assets_common` / `_pdf` | 256 / 317 | QWeb PDF reports |
| `web.assets_unit_tests` | 471 | Hoot test suites |

Directives inside a bundle list (`odoo/addons/base/models/ir_asset.py:18-23`):
`('include', bundle)`, `('remove', glob)`, `('prepend', glob)`,
`('before', target, glob)`, `('after', target, glob)`, `('replace', target, glob)`.
Globs like `web/static/src/core/**/*` are expanded per addon in dependency
order, so an addon's files always come after those of the addons it depends on.
The `ir.asset` model also lets you add bundle entries from the database.

**Building bundles.** `AssetsBundle` (`odoo/addons/base/models/assetsbundle.py:41`)
concatenates JS (`js()` `:312`), compiles SCSS (`ScssStylesheetAsset` `:1034`),
and gathers XML templates (`generate_xml_bundle()` `:387`) into one attachment
served from `/web/assets/<unique>/<bundle>.min.js`. With `?debug=assets`, files
are served unminified and with source maps.

**ES modules.** Source files are written as ES modules
(`import { registry } from "@web/core/registry"`). `odoo/tools/js_transpiler.py`
(`transpile_javascript` `:20`) rewrites each file into an
`odoo.define("@web/core/registry", [deps], function (require) {…})` call
(`wrap_with_odoo_define` `:109`). The module name comes from the file path:
`<addon>/static/src/x/y.js` becomes `@<addon>/x/y`. `ModuleLoader`
(`module_loader.js:16`, `define` `:47`, `startModules` `:210`) resolves the
dependency graph at runtime and reports missing or cyclic modules in the
console. `lib/owl/odoo_module.js` publishes the OWL global as the module
`@odoo/owl`.

**Templates.** `.xml` files in a bundle are registered with
`registerTemplate` / `registerTemplateExtension` (`core/templates.js:156,187`).
`getTemplate` (`:143`) applies inheritance (`core/template_inheritance.js`,
`applyInheritance` `:325`) the first time a template is requested. OWL calls
it through the `App` config.

## 3. OWL as Odoo uses it

OWL 2 (`lib/owl/owl.js`, version 2.8.2) is a small component framework. Its
QWeb templates compile to JS render functions, it renders through a virtual
DOM, and it has proxy-based reactivity.

```js
import { Component, useState, onWillStart, xml } from "@odoo/owl";

export class Counter extends Component {
    static template = "my_addon.Counter";        // name of an XML <t t-name="...">
    static components = { Child };               // sub-components used in the template
    static props = { start: { type: Number, optional: true } };  // validated in dev mode

    setup() {                                     // never use the constructor
        this.state = useState({ n: this.props.start ?? 0 });
        this.orm = useService("orm");             // Odoo hook (core/utils/hooks.js:142)
        onWillStart(async () => { /* async loading before first render */ });
    }
}
```

The conventions Odoo relies on:
- **Lifecycle hooks**: `onWillStart`, `onWillUpdateProps`, `onMounted`,
  `onWillPatch`, `onPatched`, `onWillUnmount`, `onWillDestroy`, `onError`.
- **Reactivity**: `useState(obj)` subscribes the component to the keys it reads
  during render. Services that return reactive objects are wrapped
  automatically by `useService` (`hooks.js:163-165`).
- **Env** is shared down the tree. `useSubEnv` / `useChildSubEnv` add keys
  (views use this for `env.config`, `env.searchModel`).
- **Templates**: `t-esc`/`t-out`, `t-if`, `t-foreach` + `t-key`, `t-on-*`,
  `t-props`, `t-slot`/`t-set-slot`, `t-ref`, `t-model`, `t-component`.
  Odoo adds the custom directive `t-custom-click`, which also handles
  middle-click and ctrl-click for "open in new tab" (`env.js:173`, `globalValues` `:196`).
- **Template inheritance** in XML:
  `<t t-inherit="web.ListRenderer" t-inherit-mode="extension">` with
  `xpath`/`position`. `primary` mode creates a new template.
- `mountComponent` (`env.js:226`) builds the `App` with `dev: env.debug`, so
  prop validation and extra checks only run in debug or test mode.

## 4. Boot sequence

1. Browser requests `/odoo` (or `/web`). `Home.web_client`
   (`addons/web/controllers/home.py:46`) renders `web.webclient_bootstrap`
   (`views/webclient_templates.xml:275`). The template inlines
   `odoo.__session_info__` (built by `ir.http.session_info()`,
   `addons/web/models/ir_http.py:79`), starts fetching
   `/web/webclient/load_menus` early, and loads `web.assets_web`.
2. `session.js:1` exposes `odoo.__session_info__` as `session`. `core/user.js:254`
   wraps it as `user` (context, groups via `user.hasGroup`, company).
3. `main.js` calls `startWebClient(WebClient)` (`start.js`). It sets
   `odoo.info`, optionally enables the browser RPC cache (`RPCCache`, keyed by
   `session.registry_hash`), waits for `whenReady()`, and then calls
   `mountComponent`.
4. `mountComponent` (`env.js:226`) calls `makeEnv()` (`:31`), which returns
   `{ bus, services: {}, debug, isReady }`, and then `startServices(env)` (`:69`):
   - It defers one microtask so that every addon's synchronous `registry.add`
     has already run.
   - It repeatedly picks the services whose `dependencies` are already started,
     calls `service.start(env, deps)` for them in parallel, and stores each
     result in `env.services[name]`.
   - It listens to registry `UPDATE` events so that services added later, from
     lazy bundles, also start.
   - It fires `SERVICES-LOADED` and reports unmet dependencies.
5. `new App(WebClient, {env, getTemplate, …}).mount(document.body)`.
   `odoo.__WOWL_DEBUG__.root` points to the root component, which is handy in
   the console.
6. `WebClient.setup()` (`webclient/webclient.js:25`) calls
   `loadRouterState()` (`:68`) on mount. It reads the URL and either restores
   the action it describes or opens the user's home action.

## 5. Registries

`core/registry.js` provides a single root `Registry` (`:209`), which extends
OWL's `EventBus`. It is a tree of categories:

- `registry.category("x")` (`:190`) creates the sub-registry on first use.
- `.add(key, value, {sequence = 50, force})` (`:99`) throws
  `DuplicatedKeyError` unless `force: true`, which is how you replace an entry.
  It triggers `UPDATE`.
- `.get(key, default)`, `.contains`, `.getAll()` / `.getEntries()` (sorted by
  sequence), `.remove`.
- `.addValidation(schema)` (`:197`) validates every entry's shape, for example
  the services registry (`env.js:53`).
- `useRegistry(reg)` (`core/registry_hook.js:3`) gives a component a reactive
  view of a category.

Categories found in `web/static/src`, by number of `.category()` call sites:

| Category | Uses | Holds |
|---|---|---|
| `fields` | 102 | field widgets, keyed `widget`, `viewType.widget` or `jsClass.widget` |
| `services` | 38 | `{ dependencies, start, async? }` |
| `formatters` / `parsers` | 12 / 2 | value ↔ string per field type |
| `views` | 11 | view descriptors, keyed by type or `js_class` |
| `view_widgets` | 10 | `<widget name="…"/>` components |
| `main_components` | 8 | always-mounted overlays (dialogs, notifications, popovers) |
| `actions` | 8 | client actions (`ir.actions.client` `tag`) |
| `systray` | 6 | navbar right-side items |
| `error_handlers` / `error_dialogs` / `error_notifications` | 5 / 1 / 2 | error pipeline |
| `command_provider` / `command_categories` / `command_setup` | 4 / 4 / 3 | Ctrl+K palette |
| `debug` | 5 | debug menu items |
| `user_menuitems`, `effects`, `dialogs`, `lazy_components`, `form_compilers`, `cogMenu` … | — | smaller extension points |

## 6. Services

A service is a singleton created once per env:

```js
export const myService = {
    dependencies: ["orm", "notification"],
    async: ["fetchThing"],          // methods whose promises are dropped once the caller is destroyed
    start(env, { orm, notification }) {
        return { fetchThing: (id) => orm.read("res.partner", [id], ["name"]) };
    },
};
registry.category("services").add("my_service", myService);
```

Components get a service with `useService(name)` (`core/utils/hooks.js:142`).
For methods listed in `async`, `useService` wraps them so that a pending
promise never resolves after the calling component has been destroyed
(`_protectMethod`). Non-component code reads `env.services.x`.

Services started in the backend client include: `action, command, currency,
datetime_picker, dialog, effect, error, field, file_upload, hotkey, http,
localization, menu, name, notification, orm, popover, profiling, sortable,
title, tooltip, ui, view` and others. The most important ones:

| Service | File | Role |
|---|---|---|
| `orm` | `core/orm_service.js:395` | `ORM` class (`:98`): `call`, `read`, `searchRead`, `create`, `write`, `unlink`, `webRead` (`:305`), `webSearchRead` (`:334`), `webReadGroup` (`:286`), `webSave` (`:361`), `.cache()` (`:115`). Everything goes to `/web/dataset/call_kw/<model>/<method>` (`:128`) |
| `rpc` (function) | `core/network/rpc.js:93` | raw JSON-RPC 2.0 helper. `rpcBus` emits `RPC:REQUEST` / `RPC:RESPONSE` and cache-clear events |
| `action` | `webclient/actions/action_service.js:1885` | `doAction`, `doActionButton`, `switchView`, `restore`, `loadState` |
| `view` | `views/view_service.js:43` | `loadViews` → `get_views` RPC (archs, fields, filters), cached |
| `field` | `core/field_service.js:20` | `loadFields`, `loadPath` (field metadata) |
| `name` | `core/name_service.js:15` | batched `display_name` loading |
| `dialog` | `core/dialog/dialog_service.js:27` | `add(Component, props, {onClose})` → returns a close function |
| `notification` | `core/notifications/notification_service.js:23` | `add(message, {type, sticky, buttons})` |
| `ui` | `core/ui/ui_service.js:164` | `isSmall`, `block/unblock`, active-element tracking (dialog focus scoping) |
| `hotkey` | `core/hotkeys/hotkey_service.js:107` | `useHotkey`, `data-hotkey` overlay (Alt shortcuts) |
| `menu` | `webclient/menus/menu_service.js:7` | menu tree from `load_menus`, current app |
| `user` (not a service) | `core/user.js:254` | context, `hasGroup` (cached RPC), settings |

## 7. Action manager and router

`makeActionManager` (`webclient/actions/action_service.js:135`) holds a
**controller stack**, one entry per breadcrumb.

- `doAction(request, options)` (`:1454`) accepts an xmlid, a numeric id, a
  client-action tag or an action dict. It loads the action via
  `/web/action/load` (`_loadAction` `:368`), normalises it
  (`_preprocessAction` `:418`, which evaluates `context` and `domain` with
  `py_js`), and dispatches on its type (`:1460-1479`):
  - `ir.actions.act_window` → `_executeActWindowAction` (`:1214`) builds a
    `View` controller for the first view type. `target: "new"` opens it in an
    `ActionDialog`.
  - `ir.actions.client` → `_executeClientAction` (`:1296`) looks up `tag` in
    `registry.category("actions")`.
  - `ir.actions.report` → `_executeReportAction` (`:1356`) downloads PDF/HTML
    via `reports/`.
  - `ir.actions.server` → `_executeServerAction` (`:1420`) calls `/web/action/run`
    and then runs the action it returns.
  - `ir.actions.act_url`, `ir.actions.act_window_close`.
- `doActionButton` (`:1508`) handles `<button type="object|action">`. It saves
  the record first, then calls the method or action and runs the result.
- `switchView` (`:1661`) swaps the view (list ↔ form) inside the same action.
  `restore` (`:1719`) is the breadcrumb click.
- `_updateUI` (`:874`) mounts the controller in `ActionContainer` and pushes
  state to the router.

**Router** (`core/browser/router.js`). URLs look like
`/odoo/action-123/42` or `/odoo/project.task/42`. `PATH_KEYS` are
`resId, action, active_id, model` (`:10`). `stateToUrl` / `urlToState`
(`:126,161`) convert in both directions, and pushes are debounced (`:342`). On
reload, `loadState` (`action_service.js:1769`) rebuilds the whole breadcrumb
stack from the URL.

## 8. Views

A **view** is a plain descriptor object registered in
`registry.category("views")`, for example `views/list/list_view.js:7`:

```js
export const listView = {
    type: "list",
    Controller: ListController,      // top-level component: control panel, buttons, record opening
    Renderer: ListRenderer,          // draws rows and cells
    ArchParser: ListArchParser,      // parses the arch XML into archInfo (columns, decorations, …)
    Model: RelationalModel,          // data layer
    buttonTemplate: "web.ListView.Buttons",
    props: (genericProps, view) => ({ ...genericProps, archInfo: new view.ArchParser().parse(...), ... }),
};
registry.category("views").add("list", listView);
```

**The `View` component** (`views/view.js:193`) is the generic entry point
used by the action manager, x2many dialogs and embedded views:
1. If the arch isn't known yet, it calls `viewService.loadViews` (`:309`),
   which returns archs, fields, related models, search view and filters.
2. It resolves the descriptor key: `js_class` attribute on the arch root →
   `props.jsClass` → `type` (`:344-346`). If the key isn't registered, it
   loads `web.assets_backend_lazy` first (`:347-352`). This is how graph and
   pivot stay out of the main bundle.
3. It sets `env.config` (`viewType`, `viewSubType = jsClass`, breadcrumbs,
   layout), builds the props (`info`, `arch`, `fields`, `resModel`,
   `searchMenuTypes`, sample mode) and calls `descr.props(...)`.
4. It wraps the controller in `WithSearch` (`search/with_search/with_search.js:8`),
   which creates the `SearchModel` (`search/search_model.js:169`): filters,
   group-bys, favourites (`ir.filters`), facets, and the resulting
   `domain/context/groupBy/orderBy` passed down as props.

**Shipped view types** in `views/`: `list`, `form`, `kanban`, `calendar`,
`graph`, `pivot`. Enterprise adds gantt, map, cohort and others. Each one
follows the same Controller / Renderer / ArchParser pattern.

**Form is compiled, not interpreted.** `FormCompiler`
(`views/form/form_compiler.js:45`), which extends `ViewCompiler`
(`views/view_compiler.js:191`), turns the arch into an OWL template string:
`<field>` → `<Field …/>`, `<group>` → `<OuterGroup>`, `<notebook>`,
`<button>` → `ViewButton`, `invisible`/`readonly`/`required` → `t-if` or
props evaluated against `record.evalContext`. `useViewCompiler` (`:452`)
caches the compiled template per arch. Kanban does the same with its card
templates. List and calendar render from `archInfo` directly.

Shared layout pieces live in `search/`: `layout.js` (control panel +
content), `control_panel/`, `breadcrumbs/`, `search_bar/`, `cog_menu/`,
`action_menus/` (the Print and Action dropdowns that show `binding_model_id`
actions), and `pager_hook.js`.

## 9. Data model (RelationalModel)

`model/model.js` defines the base `Model` (`:24`) and the hook
`useModel(ModelClass, params)` (`:104`). The hook instantiates the model with
services, calls `load()` on `onWillStart` and again on prop changes (new
domain or group-by from search), and re-renders the component when the model
`notify()`s. `useModelWithSampleData` (`:129`) swaps in `sample_server.js`
when the result is empty and `sample="1"`.

`RelationalModel` (`model/relational_model/relational_model.js:114`) is used
by form, list and kanban. Its `root` is a tree of datapoints (`datapoint.js`):

| Class | File | Represents |
|---|---|---|
| `Record` | `record.js:37` | one record. `data`, `evalContext`, `isDirty`, `update()`, `save()` (`:264`), `urgentSave()` (`:323`, on page unload) |
| `DynamicRecordList` | `dynamic_record_list.js` | ungrouped list or kanban (search + pager) |
| `DynamicGroupList` | `dynamic_group_list.js` | grouped list or kanban, with `Group` (`group.js`) per bucket |
| `StaticList` | `static_list.js` | an x2many field's value inside a record. Commands built with `x2ManyCommands` (`orm_service.js:27`) |

How the RPCs line up. Every call carries a **specification** that names the
fields to fetch, recursively for relational fields. That is how Odoo 17+
avoids N+1 reads.

```
 load() ─┬─ form, existing id   → orm.webRead(model, [id], {specification})        → model.web_read
         ├─ form, new record    → orm.call(model, "onchange", [{}, [], spec])       → model.onchange (defaults)
         ├─ list/kanban          → orm.webSearchRead(model, domain, {specification}) → model.web_search_read
         └─ grouped              → orm.webReadGroup(model, domain, groupby, aggs)    → model.web_read_group
 record.update(changes) → onchange RPC when the field has on_change (relational_model.js:693)
 record.save()          → orm.webSave(model, ids, changes, {specification})          → model.web_save (create/write + web_read)
```

Server counterparts are in `addons/web/models/models.py`: `web_search_read`
(`:66`), `web_save` (`:90`), `web_read` (`:109`), `web_read_group` (`:349`),
`onchange` (`:1965`, overriding `odoo/orm/models.py:6993`). After a write,
`relational_model.js:110` clears the RPC cache for `web_read`,
`web_search_read` and `web_read_group`.

Domains and contexts are evaluated client-side by a Python-subset interpreter
(`core/py_js/`). `Domain` is in `core/domain.js:18` and `makeContext` in
`core/context.js:23`. This is why `invisible="state != 'done'"` works without
a server round-trip.

## 10. Fields

`<field name="x" widget="y"/>` resolves through `getFieldFromRegistry`
(`views/fields/field.js:122`). It tries `jsClass.widget`, then
`viewType.widget`, then `widget`, then the same chain for the field's type,
and checks `supportedTypes`.

A field descriptor (validated at `field.js:67-84`). The shape below is
simplified; the real many2one entry is built by `buildM2OFieldDescription` and
registered at `views/fields/many2one/many2one_field.js:122`:

```js
export const many2OneField = {
    component: Many2OneField,
    displayName: _t("Many2one"),
    supportedTypes: ["many2one"],
    supportedOptions: [{ label, name: "no_create", type: "boolean" }, …],  // shown in Studio / debug
    extractProps: (staticInfo, dynamicInfo) => ({ canCreate: !staticInfo.options.no_create, … }),
    fieldDependencies: [...],          // extra fields to fetch
    isEmpty: (record, fieldName) => …, // for the "o_field_empty" class
    relatedFields: [...],              // sub-specification for relational fields
};
registry.category("fields").add("many2one", many2OneField);
```

The `Field` wrapper component (`field.js:221`) computes the props. Every
widget receives `standardFieldProps` (`standard_field_props.js:9`): `name`,
`record`, `readonly`, `id`. A widget reads `props.record.data[props.name]` and
writes with `props.record.update({ [name]: value })`. It never calls the ORM
directly for its own value.

Formatting and parsing are separate registries (`formatters.js`,
`parsers.js`, keyed by field type). Notable widgets: `many2one/`
(`many2one_field.js:95`, autocomplete + quick create), `many2many_tags/`,
`properties/` (the `task_properties` editor used by `project.task`), `html/`,
`statusbar`, `priority`, `boolean_toggle`, `monetary`, `image`, `pdf_viewer`.
Non-field `<widget name="…"/>` elements use `view_widgets` (`views/widgets/`).

## 11. Core UI components

All of these live in `core/` and are reusable from any addon:

- `dialog/`: `Dialog` component plus `dialog` service. `confirmation_dialog/`
  provides `ConfirmationDialog` and `AlertDialog`.
- `dropdown/`: `Dropdown`, `DropdownItem`, `useDropdownState`.
- `popover/`, `overlay/`, `position/`: anchored overlays with the
  `usePopover` hook. `tooltip/` reads `data-tooltip` attributes.
- `notifications/`, `effects/` (rainbow man), `bottom_sheet/` (mobile).
- `autocomplete/`, `select_menu/`, `tags_list/`, `record_selectors/`,
  `domain_selector/`, `tree_editor/`, `model_field_selector/`,
  `datetime/` (luxon-based picker), `color_picker/`, `file_upload/`,
  `file_viewer/`, `signature/`, `pager/`, `notebook/`, `code_editor/` (ace).
- `commands/`: the Ctrl+K command palette, extended via `command_provider`.
- `main_components_container.js` mounts everything in
  `registry.category("main_components")` once at the root (dialog container,
  notification container, popovers, loading indicator).
- `utils/`: `hooks.js` (`useService`, `useBus` `:87`, `useAutofocus`,
  `useOwnedDialogs` `:257`), `patch.js`, `concurrency.js` (`KeepLast`,
  `Mutex`), `timing.js` (`debounce`), `strings.js`, `arrays.js`, `urls.js`.

## 12. Patching and extension

From least to most invasive:

| Need | Mechanism | Example |
|---|---|---|
| New behaviour on one view only | Subclass the controller or renderer, register a new descriptor, and set `js_class` on the arch | `serichai_restricted_task_list` (§16) |
| New field widget or variant | `registry.category("fields").add("my_widget", {...})` | |
| Replace a registry entry globally | `.add(key, value, { force: true })` | |
| Change a class everywhere | `patch(Class.prototype, { method() { super.method(...arguments); … } })` | MuK `chatter.js`, `navbar.js` |
| Change static members | `patch(Class, { components: {...Class.components, X} })` | `muk_web_appsbar/static/src/webclient/webclient.js` |
| Change markup | XML `t-inherit` + `t-inherit-mode="extension"` with `xpath` | |
| Change server-provided arch | standard `ir.ui.view` inheritance (server side) | |

`patch(obj, extension)` (`core/utils/patch.js:71`) copies property
descriptors onto the target and keeps a skeleton chain so `super` works across
several patches. It returns an `unpatch` function, which tests use. Patches
apply in bundle order, which is addon dependency order. Patch the
**prototype** for instance methods. `setup()` is the usual hook point, but
remember to call `super.setup()`.

## 13. Errors and debug

- The `error` service (`core/errors/error_service.js`) catches unhandled
  rejections, window errors and OWL `onError`. It runs the handlers in
  `error_handlers` by sequence (`core/errors/error_handlers.js:21`):
  `rpcErrorHandler` (`:35`) maps server exception names to dialogs via
  `error_dialogs` (e.g. `odoo.exceptions.AccessError`, `ValidationError`,
  `RedirectWarning`). `lostConnectionHandler` (`:96`) shows the reconnecting
  banner. `defaultHandler` (`:172`) is the fallback.
- A Python `UserError` raised in an override (such as the `web_read` guard in
  §16) arrives as an `RPC_ERROR` and is shown as a dialog. Nothing extra is
  needed on the client.
- Debug modes: `?debug=1` (developer tools menu, `core/debug/`,
  `registry.category("debug")`) and `?debug=assets` (unminified, source maps,
  OWL dev mode with prop validation). `?debug=tests` loads the tour bundles.
- In the console, `odoo.__WOWL_DEBUG__.root` is the root component.
  `odoo.loader.modules` lists the loaded modules.

## 14. Testing (Hoot)

Odoo 19 tests the frontend with **Hoot** (`lib/hoot/`, `lib/hoot-dom/`), its
own Jest-like runner. QUnit (`lib/qunit/`, `tests/legacy/`) remains only for
older suites.

- Tests are `*.test.js` files under `<addon>/static/tests/`, added to the
  `web.assets_unit_tests` bundle (`__manifest__.py:471`). They run at
  `/web/tests` in a browser, or headless through the Python `HttpCase`
  runner.
- Helpers are exported from `@web/../tests/web_test_helpers` (`tests/web_test_helpers.js`):
  `defineModels` (Python-like mock models), `onRpc` (intercept a route or
  method), `mockService`, `mountWithCleanup` (`_framework/component_test_helpers.js:114`),
  `mountView` (`_framework/view_test_helpers.js:239`, which mounts a view from
  an arch string), `contains(selector).click()` and others.
- Tours (`web_tour`, `*.tour.js`) drive the real UI end to end and are
  launched from Python `HttpCase.start_tour`.

## 15. Bundled third-party libraries (`web/static/lib/`)

`owl` (2.8.2), `luxon` (dates, used everywhere instead of moment), `bootstrap`
(SCSS + selected JS modules), `popper`, `Chart` + `chartjs-adapter-luxon`
(graph view), `fullcalendar` (calendar view), `pdfjs`, `ace`, `dompurify`
(HTML sanitising), `prismjs`, `signature_pad`, `zxing-library` (barcode),
`stacktracejs`, `diff_match_patch`, `jquery` (legacy, kept only for website
and frontend code), `hoot`/`hoot-dom`/`qunit` (tests).

## 16. Implications for this repo

**`serichai_restricted_task_list`**
(`serichai_project_security/static/src/views/restricted_task_list.js`) is a
textbook `js_class` extension:
- It spreads `listView` and replaces only `Controller` with
  `RestrictedTaskListController`, which extends `ListController`.
- It overrides `openRecord(record, {force, newWindow})`, which has the same
  signature as `views/list/list_controller.js:344`. The renderer reaches it
  through `props.openRecord` from `onCellClicked`
  (`views/list/list_renderer.js:1221,1268`). Overriding at the controller
  level therefore covers clicks, keyboard Enter and the form pager's
  `activeIds`.
- `record.data.is_expanded_access_task` only exists because the field is in
  the list arch (`views/project_task_views.xml:25`, `column_invisible="1"`), so
  it is part of the `web_search_read` specification. If that column is removed,
  the check silently sees `undefined` and blocks every row.
- It is loaded through `web.assets_backend` in the manifest. The arch selects
  it with `js_class="serichai_restricted_task_list"`.

**Server-side guard and the RPC shapes.** A form load is a top-level
`orm.webRead` → `/web/dataset/call_kw/project.task/web_read`. Lists and kanban
call `web_search_read`, and grouped views call `web_read_group`. Both reach
`web_read` internally on the server (`models.py:68`). That is why
`_is_restricted_form_load()` inspects `request.params` (the top-level
`method`) instead of guarding `web_read` unconditionally. A future view type
that calls `webRead` directly, such as a custom dashboard or a Many2One
quick-open dialog, would also hit the guard.

**MuK theme.** The MuK addons use the supported extension mechanisms:
`patch()` on `WebClient` (appsbar), `NavBar`, `FormRenderer` /
`FormCompiler` (chatter position), `Dialog` and the mail `Thread`/`Composer`;
new services (`app_menu`, `muk_web_refresh.reload`); and `cogMenu` entries
(group expand/collapse). Because they patch core classes, Odoo point-release
upgrades can break them silently. Re-test the chatter and the appsbar after
updating `odoo/`.

**Recommended patterns for new frontend work here:**
- Prefer `js_class` and a subclassed descriptor for anything specific to one
  view. Use `patch()` only when the behaviour must apply everywhere, and never
  edit `odoo/addons/web` directly.
- Put JS, XML and SCSS under `<addon>/static/src/`, mirroring the core
  path (`views/`, `fields/`, `services/`), and list them under
  `'web.assets_backend'` in `__manifest__.py` (globs such as
  `'my_addon/static/src/**/*'` are fine).
- Use `useService("orm")` with `webSearchRead`/`webRead` and an explicit
  specification rather than `searchRead` with field lists. Use `async:`
  method lists on new services so late responses don't hit destroyed
  components.
- Enforce access on the server (record rules, `web_read` guard). Client-side
  checks such as greying rows are UX only, because every RPC can be replayed.
- Add Hoot tests under `<addon>/static/tests/` with `mountView` +
  `onRpc` for any new controller logic. No frontend tests exist in the custom
  addons yet.
