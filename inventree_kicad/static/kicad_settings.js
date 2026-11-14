/**
 * Custom settings panel for the KiCad Library plugin.
 *
 * - Supplier selection: lets the user select which suppliers are included in the KiCad
 *   manufacturer / supplier data. The selection is stored by the plugin
 *   (as plugin metadata) via the plugin's own supplier-filter API endpoint.
 *   An empty selection means that all suppliers are included.
 * - Stock count display format: editor for the KICAD_ENABLE_STOCK_COUNT_FORMAT setting,
 *   with placeholder autocompletion and a live preview.
 * - KiCad field names: table which renames fields sent to KiCad (e.g. IPN -> SKU),
 *   stored as plugin metadata via the plugin's field-mapping API endpoint.
 */

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
}

function isTrue(value) {
    return ['true', '1', 'yes', 'on'].includes(String(value).toLowerCase());
}

const INPUT_STYLE = `padding: 6px 10px; border-radius: 4px;
    border: 1px solid var(--mantine-color-default-border, #ccc);
    background: var(--mantine-color-body, #fff);
    color: var(--mantine-color-text, inherit);`;

// Placeholders offered by the stock count format autocompletion (without the braces)
const STOCK_PLACEHOLDERS = [
    { text: '0', description: 'Part description' },
    { text: '1', description: 'Unallocated stock' },
    { text: 'part.name', description: 'Part name' },
    { text: 'part.IPN', description: 'Internal part number' },
    { text: 'part.description', description: 'Part description' },
    { text: 'part.stock', description: 'Unallocated stock (number)' },
    { text: 'part.stock:.0f', description: 'Unallocated stock, no decimals' },
    { text: 'part.revision', description: 'Part revision' },
    { text: 'part.used_in', description: 'Number of assemblies using this part (slower)' },
];

/**
 * Add placeholder autocompletion to a text input: typing "{" lists the placeholders,
 * which are inserted with the arrow keys and Enter / Tab, or by clicking them.
 *
 * Works for inputs controlled by React (InvenTree's setting dialog) as well: the value is set
 * through the native setter and an "input" event is dispatched, so React picks up the change.
 */
function attachPlaceholderAutocomplete(input, placeholders) {
    const valueSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;

    let menu = null;
    let matches = [];
    let activeIndex = 0;

    // Return the placeholder being typed at the caret, i.e. the text after an unclosed "{"
    function currentToken() {
        if (input.selectionStart !== input.selectionEnd) {
            return null;
        }

        const caret = input.selectionStart ?? input.value.length;
        const before = input.value.slice(0, caret);
        const open = before.lastIndexOf('{');

        // No brace, or an escaped brace ("{{")
        if (open < 0 || before[open - 1] === '{') {
            return null;
        }

        const token = before.slice(open + 1);

        if (!/^[\w.:]*$/.test(token)) {
            return null;
        }

        return { start: open + 1, end: caret, token };
    }

    function closeMenu() {
        menu?.remove();
        menu = null;
        matches = [];
    }

    function renderMenu() {
        if (!menu) {
            // Attached to the body with a fixed position, so it is not clipped by dialogs
            menu = document.createElement('div');
            menu.style.cssText = `position: fixed; z-index: 10000; max-height: 240px; overflow-y: auto;
                border-radius: 4px; border: 1px solid var(--mantine-color-default-border, #ccc);
                background: var(--mantine-color-body, #fff); color: var(--mantine-color-text, inherit);
                box-shadow: 0 4px 12px rgba(0,0,0,.15); font-size: 14px;`;

            // mousedown (not click), so the input keeps the focus and the caret position
            menu.addEventListener('mousedown', (event) => {
                event.preventDefault();
                const index = parseInt(event.target.closest('[data-index]')?.dataset?.index, 10);
                if (!Number.isNaN(index)) {
                    accept(matches[index]);
                }
            });

            document.body.appendChild(menu);
        }

        const rect = input.getBoundingClientRect();
        menu.style.left = `${rect.left}px`;
        menu.style.top = `${rect.bottom + 2}px`;
        menu.style.width = `${rect.width}px`;

        menu.innerHTML = matches
            .map(
                (p, i) => `<div data-index="${i}" style="display: flex; justify-content: space-between; gap: 12px;
                    padding: 4px 10px; cursor: pointer;
                    ${i === activeIndex ? 'background: var(--mantine-primary-color-light, #e7f5ff);' : ''}">
                    <span style="font-family: monospace;">{${escapeHtml(p.text)}}</span>
                    <span style="font-size: 0.85em; opacity: 0.75;">${escapeHtml(p.description)}</span>
                </div>`
            )
            .join('');

        menu.querySelector(`[data-index="${activeIndex}"]`)?.scrollIntoView({ block: 'nearest' });
    }

    function updateMenu() {
        const token = currentToken();

        if (!token) {
            closeMenu();
            return;
        }

        const query = token.token.toLowerCase();
        const closed = input.value[token.end] === '}';

        // Placeholders starting with the typed text first, then those containing it
        const startsWith = placeholders.filter((p) => p.text.toLowerCase().startsWith(query));
        const contains = placeholders.filter(
            (p) => !startsWith.includes(p)
                && (p.text.toLowerCase().includes(query) || p.description.toLowerCase().includes(query))
        );
        const found = [...startsWith, ...contains];

        // Nothing to suggest, or the placeholder is already complete
        if (found.length === 0 || (closed && found.some((p) => p.text === token.token))) {
            closeMenu();
            return;
        }

        matches = found;
        activeIndex = Math.min(activeIndex, matches.length - 1);
        renderMenu();
    }

    function accept(placeholder) {
        const token = currentToken();

        if (!token) {
            return;
        }

        const value = input.value;
        const closing = value[token.end] === '}' ? '' : '}';
        const caret = token.start + placeholder.text.length + 1;

        closeMenu();

        valueSetter.call(input, value.slice(0, token.start) + placeholder.text + closing + value.slice(token.end));
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.setSelectionRange(caret, caret);
    }

    input.setAttribute('autocomplete', 'off');

    input.addEventListener('input', () => {
        activeIndex = 0;
        updateMenu();
    });

    input.addEventListener('keydown', (event) => {
        if (matches.length === 0) {
            return;
        }

        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            const step = event.key === 'ArrowDown' ? 1 : -1;
            activeIndex = (activeIndex + step + matches.length) % matches.length;
            renderMenu();
        } else if (event.key === 'Enter' || event.key === 'Tab') {
            // Also keeps Enter from submitting the setting dialog
            accept(matches[activeIndex]);
        } else if (event.key === 'Escape') {
            // Close only the suggestions, not the setting dialog
            closeMenu();
        } else {
            return;
        }

        event.preventDefault();
        event.stopPropagation();
    });

    // Caret moved without changing the text
    input.addEventListener('keyup', (event) => {
        if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
            updateMenu();
        }
    });
    input.addEventListener('click', updateMenu);
    input.addEventListener('blur', closeMenu);
}

/**
 * Add placeholder autocompletion to InvenTree's "Edit Setting" dialog for the given setting.
 * The dialog is rendered by InvenTree, so we watch the page for it to open.
 * Stops watching once the settings panel has been closed.
 */
function watchSettingDialog(panel, settingName, placeholders) {
    let scheduled = false;

    function enhance() {
        scheduled = false;

        document.querySelectorAll('[role="dialog"]').forEach((dialog) => {
            if (!dialog.textContent.includes(settingName)) {
                return;
            }

            const input = dialog.querySelector('input:not([type]), input[type="text"]');

            if (input && !input.dataset.kicadAutocomplete) {
                input.dataset.kicadAutocomplete = 'true';
                attachPlaceholderAutocomplete(input, placeholders);
            }
        });
    }

    const observer = new MutationObserver(() => {
        if (!document.body.contains(panel)) {
            observer.disconnect();
        } else if (!scheduled) {
            scheduled = true;
            requestAnimationFrame(enhance);
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
    enhance();
}

export function renderPluginSettings(target, data) {
    const api = data.api;
    const context = data.context ?? {};
    const filterUrl = context.supplier_filter_url ?? '/plugin/kicad-library-plugin/api/supplier-filter/';
    const enableSettingUrl = context.enable_setting_url
        ?? '/api/plugins/kicad-library-plugin/settings/KICAD_ENABLE_MANUFACTURER_DATA/';

    target.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 24px;">
        <div data-role="supplier-section"></div>
        <div data-role="stock-section"></div>
        <div data-role="field-mapping-section"></div>
    </div>
    `;

    const stockEditor = renderStockFormatEditor(target.querySelector('[data-role="stock-section"]'), api, context);
    renderFieldMappingEditor(target.querySelector('[data-role="field-mapping-section"]'), api, context);

    // The regular settings list edits the format in a dialog: add the autocompletion there as well
    watchSettingDialog(target, context.stock_format_setting_name ?? 'Stock Count Display Format', STOCK_PLACEHOLDERS);

    const supplierSection = target.querySelector('[data-role="supplier-section"]');

    let suppliers = [];
    let selected = new Set();
    let saveTimer = null;

    supplierSection.innerHTML = `
    <div data-role="disabled-note" style="display: none; font-size: 0.9em; opacity: 0.75;">
        Enable "Add Manufacturer Data to KiCad Parts" in the plugin settings to select the suppliers
        whose data is added to KiCad parts.
    </div>
    <div data-role="content" style="display: none; flex-direction: column; gap: 8px;">
        <div>
            <strong>Manufacturer Data Suppliers</strong>
            <div style="font-size: 0.85em; opacity: 0.75;">
                Only data from the selected suppliers is added to KiCad parts
                (requires "Add Manufacturer Data to KiCad Parts").
                If no supplier is selected, all suppliers are included.
            </div>
        </div>
        <div data-role="selected" style="display: flex; flex-wrap: wrap; gap: 4px;"></div>
        <div style="display: flex; gap: 8px; align-items: center;">
            <input data-role="search" type="search" placeholder="Filter suppliers..."
                style="flex: 1; ${INPUT_STYLE}" />
            <button data-role="clear" type="button"
                style="padding: 6px 10px; border-radius: 4px; cursor: pointer;
                       border: 1px solid var(--mantine-color-default-border, #ccc);
                       background: var(--mantine-color-default, #fff);
                       color: var(--mantine-color-text, inherit);">Clear selection</button>
        </div>
        <div data-role="list"
            style="max-height: 300px; overflow-y: auto; padding: 4px 8px; border-radius: 4px;
                   border: 1px solid var(--mantine-color-default-border, #ccc);"></div>
        <div data-role="status" style="font-size: 0.85em; opacity: 0.75;">Loading suppliers...</div>
    </div>
    `;

    const searchInput = supplierSection.querySelector('[data-role="search"]');
    const listDiv = supplierSection.querySelector('[data-role="list"]');
    const selectedDiv = supplierSection.querySelector('[data-role="selected"]');
    const statusDiv = supplierSection.querySelector('[data-role="status"]');
    const clearButton = supplierSection.querySelector('[data-role="clear"]');
    const contentDiv = supplierSection.querySelector('[data-role="content"]');
    const disabledNote = supplierSection.querySelector('[data-role="disabled-note"]');

    function setEnabled(value) {
        const enabled = isTrue(value);
        contentDiv.style.display = enabled ? 'flex' : 'none';
        disabledNote.style.display = enabled ? 'none' : 'block';
        return enabled;
    }

    // Small notification, styled like the InvenTree (Mantine) notifications.
    // Plugins have no access to the InvenTree notification system, so we render our own.
    function showNotification(title, message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed; right: 16px; bottom: 120px; z-index: 10000;
            width: 440px; max-width: calc(100vw - 32px); box-sizing: border-box;
            display: flex; gap: 12px; align-items: flex-start;
            padding: 10px 12px 10px 18px; border-radius: 4px;
            background: var(--mantine-color-body, #fff);
            color: var(--mantine-color-text, inherit);
            box-shadow: 0 1px 3px rgba(0,0,0,.05), 0 10px 15px -5px rgba(0,0,0,.1), 0 7px 7px -5px rgba(0,0,0,.04);
            border-left: 6px solid var(--mantine-color-blue-filled, #228be6);
            font-family: var(--mantine-font-family, inherit);`;
        toast.innerHTML = `
            <div style="flex: 1;">
                <div style="font-weight: 500; font-size: 0.9em; margin-bottom: 2px;">${escapeHtml(title)}</div>
                <div style="font-size: 0.85em; color: var(--mantine-color-dimmed, #868e96);">${escapeHtml(message)}</div>
            </div>
            <button type="button" title="Close"
                style="border: none; background: none; cursor: pointer; font-size: 18px; line-height: 1;
                       color: var(--mantine-color-dimmed, #868e96);">&times;</button>`;

        const close = () => toast.remove();
        toast.querySelector('button').addEventListener('click', close);
        document.body.appendChild(toast);
        setTimeout(close, 8000);
    }

    // The settings list and this panel are separate components, so there is no change event.
    // Instead, watch the shared API client for the requests which save the relevant settings
    // in the settings list, and update the panel immediately.
    const interceptor = api.interceptors.response.use((response) => {
        if (!document.body.contains(target)) {
            // Panel has been closed - remove the interceptor
            api.interceptors.response.eject(interceptor);
        } else if (['patch', 'put'].includes(response?.config?.method)) {
            const url = String(response?.config?.url ?? '');

            if (url.endsWith(enableSettingUrl) && setEnabled(response.data?.value)) {
                showNotification(
                    'Supplier selection available',
                    'You can now select specific suppliers in "Plugin Configuration" further down. '
                    + 'If no supplier is selected, data from all suppliers is added to KiCad parts.'
                );
            }

            if (stockEditor.handleSettingSaved(url, response.data?.value)) {
                showNotification(
                    'Stock format editor available',
                    'You can now edit the stock count display format, with autocompletion and preview, '
                    + 'in "Plugin Configuration" further down.'
                );
            }
        }
        return response;
    });

    function setStatus(text) {
        statusDiv.textContent = text;
    }

    function supplierName(id) {
        return suppliers.find((s) => s.pk === id)?.name ?? `#${id}`;
    }

    function renderSelected() {
        if (selected.size === 0) {
            selectedDiv.innerHTML = '<em style="opacity: 0.75;">No filter - all suppliers are included</em>';
            return;
        }

        selectedDiv.innerHTML = [...selected]
            .map((id) => ({ id, name: supplierName(id) }))
            .sort((a, b) => a.name.localeCompare(b.name))
            .map(
                (s) => `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px;
                    border-radius: 12px; font-size: 0.85em;
                    background: var(--mantine-primary-color-light, #e7f5ff);
                    color: var(--mantine-primary-color-light-color, inherit);">
                    ${escapeHtml(s.name)}
                    <a href="#" data-remove="${s.id}" title="Remove"
                       style="text-decoration: none; color: inherit; font-weight: bold;">&times;</a>
                </span>`
            )
            .join('');
    }

    function renderList() {
        const filter = searchInput.value.trim().toLowerCase();
        const matches = suppliers.filter((s) => !filter || s.name.toLowerCase().includes(filter));

        if (matches.length === 0) {
            listDiv.innerHTML = '<em style="opacity: 0.75;">No matching suppliers</em>';
            return;
        }

        listDiv.innerHTML = matches
            .map(
                (s) => `<label style="display: flex; align-items: center; gap: 8px; padding: 2px 0; cursor: pointer;">
                    <input type="checkbox" data-id="${s.pk}" ${selected.has(s.pk) ? 'checked' : ''} />
                    ${escapeHtml(s.name)}
                </label>`
            )
            .join('');
    }

    function save() {
        clearTimeout(saveTimer);
        saveTimer = setTimeout(() => {
            setStatus('Saving...');
            api.put(filterUrl, { suppliers: [...selected] })
                .then(() => setStatus(`Saved - ${selected.size || 'all'} supplier(s) included`))
                .catch((error) => setStatus(`Error saving selection: ${error?.message ?? error}`));
        }, 400);
    }

    function toggle(id, checked) {
        if (checked) {
            selected.add(id);
        } else {
            selected.delete(id);
        }
        renderSelected();
        save();
    }

    searchInput.addEventListener('input', renderList);

    listDiv.addEventListener('change', (event) => {
        const id = parseInt(event.target?.dataset?.id, 10);
        if (!Number.isNaN(id)) {
            toggle(id, event.target.checked);
        }
    });

    selectedDiv.addEventListener('click', (event) => {
        const id = parseInt(event.target?.dataset?.remove, 10);
        if (!Number.isNaN(id)) {
            event.preventDefault();
            toggle(id, false);
            renderList();
        }
    });

    clearButton.addEventListener('click', () => {
        selected = new Set();
        renderSelected();
        renderList();
        save();
    });

    api.get(enableSettingUrl)
        .then((response) => setEnabled(response.data?.value))
        .catch(() => setEnabled(true));

    Promise.all([
        api.get('/api/company/', { params: { is_supplier: true, ordering: 'name' } }),
        api.get(filterUrl)
    ])
        .then(([companyResponse, filterResponse]) => {
            const results = companyResponse.data?.results ?? companyResponse.data ?? [];
            suppliers = results.map((c) => ({ pk: c.pk, name: c.name }));
            selected = new Set(filterResponse.data?.suppliers ?? []);

            renderSelected();
            renderList();
            setStatus(`${suppliers.length} suppliers available`);
        })
        .catch((error) => setStatus(`Error loading suppliers: ${error?.message ?? error}`));
}

/**
 * Editor for the stock count display format, with placeholder autocompletion
 * (triggered by typing "{") and a live preview rendered by the server.
 *
 * Returns { handleSettingSaved(url, value) }, which keeps the editor in sync with
 * changes made in the regular settings list. It returns true if the editor just became available.
 */
function renderStockFormatEditor(section, api, context) {
    const enableUrl = context.stock_enable_setting_url
        ?? '/api/plugins/kicad-library-plugin/settings/KICAD_ENABLE_STOCK_COUNT/';
    const formatUrl = context.stock_format_setting_url
        ?? '/api/plugins/kicad-library-plugin/settings/KICAD_ENABLE_STOCK_COUNT_FORMAT/';
    const previewUrl = context.stock_format_preview_url
        ?? '/plugin/kicad-library-plugin/api/stock-format-preview/';

    section.innerHTML = `
    <div data-role="disabled-note" style="display: none; font-size: 0.9em; opacity: 0.75;">
        Enable "Display Available Stock" in the plugin settings to edit the stock count display format
        with autocompletion and preview.
    </div>
    <div data-role="content" style="display: none; flex-direction: column; gap: 8px;">
        <div>
            <strong>Stock Count Display Format</strong>
            <div style="font-size: 0.85em; opacity: 0.75;">
                Shown as the part description in the KiCad symbol chooser.
                Type <code>{</code> to insert a placeholder. Changes are saved automatically once the format is valid.
            </div>
        </div>
        <div style="position: relative;">
            <input data-role="format" type="text" spellcheck="false" autocomplete="off"
                style="width: 100%; box-sizing: border-box; font-family: monospace; ${INPUT_STYLE}" />
        </div>
        <div style="font-size: 0.85em;">
            <span style="opacity: 0.75;">Preview (example part):</span>
            <span data-role="preview" style="font-family: monospace;"></span>
        </div>
        <div data-role="status" style="font-size: 0.85em; opacity: 0.75;"></div>
    </div>
    `;

    const input = section.querySelector('[data-role="format"]');
    const previewSpan = section.querySelector('[data-role="preview"]');
    const statusDiv = section.querySelector('[data-role="status"]');
    const contentDiv = section.querySelector('[data-role="content"]');
    const disabledNote = section.querySelector('[data-role="disabled-note"]');

    let enabled = false;
    let savedValue = null;
    let previewTimer = null;
    let previewSeq = 0;

    function setEnabled(value) {
        enabled = isTrue(value);
        contentDiv.style.display = enabled ? 'flex' : 'none';
        disabledNote.style.display = enabled ? 'none' : 'block';
        return enabled;
    }

    function setStatus(text) {
        statusDiv.textContent = text;
    }

    attachPlaceholderAutocomplete(input, STOCK_PLACEHOLDERS);
    input.addEventListener('input', schedulePreview);

    // --- Preview and saving ---

    function schedulePreview() {
        clearTimeout(previewTimer);
        previewTimer = setTimeout(updatePreview, 300);
    }

    function updatePreview() {
        const value = input.value;
        const seq = ++previewSeq;

        api.post(previewUrl, { format: value })
            .then((response) => {
                if (seq !== previewSeq) {
                    return;
                }

                previewSpan.style.color = '';
                previewSpan.textContent = response.data?.preview || '(empty)';
                save(value);
            })
            .catch((error) => {
                if (seq !== previewSeq) {
                    return;
                }

                previewSpan.style.color = 'var(--mantine-color-red-text, #e03131)';
                previewSpan.textContent = error?.response?.data?.error ?? error?.message ?? String(error);
                setStatus(value === savedValue ? '' : 'Not saved - the format is invalid');
            });
    }

    function save(value) {
        if (value === savedValue) {
            setStatus('');
            return;
        }

        setStatus('Saving...');
        api.patch(formatUrl, { value })
            .then(() => {
                savedValue = value;
                setStatus('Saved');
            })
            .catch((error) => setStatus(`Error saving format: ${error?.message ?? error}`));
    }

    function loadFormat() {
        return api.get(formatUrl).then((response) => {
            input.value = response.data?.value ?? '';
            savedValue = input.value;
            updatePreview();
        });
    }

    api.get(enableUrl)
        .then((response) => {
            if (setEnabled(response.data?.value)) {
                loadFormat();
            }
        })
        .catch(() => setStatus('Error loading the stock count settings'));

    return {
        handleSettingSaved(url, value) {
            if (url.endsWith(enableUrl)) {
                const wasEnabled = enabled;

                if (setEnabled(value) && !wasEnabled) {
                    loadFormat();
                    return true;
                }
            } else if (url.endsWith(formatUrl) && document.activeElement !== input) {
                // Saved from the regular settings list
                input.value = value ?? '';
                savedValue = input.value;
                updatePreview();
            }

            return false;
        },
    };
}

/**
 * Table which renames fields sent to KiCad (issue #169), e.g. IPN -> SKU.
 * Without any rows, the fields are sent unchanged.
 */
function renderFieldMappingEditor(section, api, context) {
    const mappingUrl = context.field_mapping_url ?? '/plugin/kicad-library-plugin/api/field-mapping/';
    const datalistId = `kicad-field-names-${Math.random().toString(36).slice(2)}`;

    const BUTTON_STYLE = `padding: 4px 10px; border-radius: 4px; cursor: pointer;
        border: 1px solid var(--mantine-color-default-border, #ccc);
        background: var(--mantine-color-default, #fff);
        color: var(--mantine-color-text, inherit);`;

    section.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 8px;">
        <div>
            <strong>KiCad Field Names</strong>
            <div style="font-size: 0.85em; opacity: 0.75;">
                Rename fields sent to KiCad, e.g. <code>IPN</code> &rarr; <code>SKU</code>.
                Field names are matched case-insensitively. Without any rows, all fields keep their names.
                Changes are saved automatically.
            </div>
        </div>
        <datalist id="${datalistId}"></datalist>
        <div data-role="rows" style="display: flex; flex-direction: column; gap: 6px;"></div>
        <div>
            <button data-role="add" type="button" style="${BUTTON_STYLE}">Add field</button>
        </div>
        <div data-role="status" style="font-size: 0.85em; opacity: 0.75;">Loading field mapping...</div>
    </div>
    `;

    const datalist = section.querySelector('datalist');
    const rowsDiv = section.querySelector('[data-role="rows"]');
    const statusDiv = section.querySelector('[data-role="status"]');
    const addButton = section.querySelector('[data-role="add"]');

    let rows = [];
    let saveTimer = null;
    let saveSeq = 0;

    function setStatus(text) {
        statusDiv.textContent = text;
    }

    function renderRows() {
        if (rows.length === 0) {
            rowsDiv.innerHTML = '<em style="font-size: 0.9em; opacity: 0.75;">No fields renamed</em>';
            return;
        }

        rowsDiv.innerHTML = rows
            .map(
                (row, i) => `<div data-row="${i}" style="display: flex; flex-direction: column; gap: 2px;">
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <input data-field="from" type="text" list="${datalistId}" autocomplete="off"
                            placeholder="InvenTree field (e.g. IPN)" value="${escapeHtml(row.from)}"
                            style="flex: 1; min-width: 0; ${INPUT_STYLE}" />
                        <span style="opacity: 0.75;">&rarr;</span>
                        <input data-field="to" type="text" autocomplete="off"
                            placeholder="KiCad field (e.g. SKU)" value="${escapeHtml(row.to)}"
                            style="flex: 1; min-width: 0; ${INPUT_STYLE}" />
                        <button data-remove="${i}" type="button" title="Remove" style="${BUTTON_STYLE}">&times;</button>
                    </div>
                    <div data-role="error" style="font-size: 0.85em; color: var(--mantine-color-red-text, #e03131);"></div>
                </div>`
            )
            .join('');
    }

    function showErrors(errors) {
        rowsDiv.querySelectorAll('[data-row]').forEach((rowDiv) => {
            rowDiv.querySelector('[data-role="error"]').textContent = errors[rowDiv.dataset.row] ?? '';
        });
    }

    function save() {
        clearTimeout(saveTimer);
        saveTimer = setTimeout(() => {
            const seq = ++saveSeq;

            // Rows which are not filled in completely yet are not sent
            const complete = rows
                .map((row, index) => ({ index, from: row.from.trim(), to: row.to.trim() }))
                .filter((row) => row.from && row.to);

            setStatus('Saving...');
            showErrors({});

            api.put(mappingUrl, { mapping: complete.map(({ from, to }) => ({ from, to })) })
                .then(() => {
                    if (seq !== saveSeq) {
                        return;
                    }

                    const incomplete = rows.length - complete.length;
                    setStatus(incomplete
                        ? `Saved - ${incomplete} incomplete row(s) not used yet`
                        : `Saved - ${complete.length || 'no'} field(s) renamed`);
                })
                .catch((error) => {
                    if (seq !== saveSeq) {
                        return;
                    }

                    const errors = error?.response?.data?.errors;

                    if (errors && typeof errors === 'object') {
                        // Map the indexes of the sent rows back to the rows in the table
                        const rowErrors = {};
                        Object.entries(errors).forEach(([index, message]) => {
                            const row = complete[parseInt(index, 10)];
                            if (row) {
                                rowErrors[row.index] = message;
                            }
                        });
                        showErrors(rowErrors);
                        setStatus('Not saved - fix the highlighted rows');
                    } else {
                        setStatus(`Error saving field mapping: ${error?.message ?? error}`);
                    }
                });
        }, 400);
    }

    rowsDiv.addEventListener('input', (event) => {
        const rowDiv = event.target.closest('[data-row]');
        const field = event.target.dataset?.field;

        if (rowDiv && field) {
            rows[parseInt(rowDiv.dataset.row, 10)][field] = event.target.value;
            save();
        }
    });

    rowsDiv.addEventListener('click', (event) => {
        const index = parseInt(event.target?.dataset?.remove, 10);

        if (!Number.isNaN(index)) {
            rows.splice(index, 1);
            renderRows();
            save();
        }
    });

    addButton.addEventListener('click', () => {
        rows.push({ from: '', to: '' });
        renderRows();
        rowsDiv.querySelector(`[data-row="${rows.length - 1}"] [data-field="from"]`)?.focus();
    });

    api.get(mappingUrl)
        .then((response) => {
            rows = (response.data?.mapping ?? []).map((row) => ({ from: row.from, to: row.to }));
            datalist.innerHTML = (response.data?.suggestions ?? [])
                .map((name) => `<option value="${escapeHtml(name)}"></option>`)
                .join('');

            renderRows();
            setStatus(rows.length ? `${rows.length} field(s) renamed` : '');
        })
        .catch((error) => setStatus(`Error loading field mapping: ${error?.message ?? error}`));
}
