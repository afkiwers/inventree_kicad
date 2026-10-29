/**
 * Custom settings panel for the KiCad Library plugin.
 *
 * Lets the user select which suppliers are included in the KiCad
 * manufacturer / supplier data. The selection is stored by the plugin
 * (as plugin metadata) via the plugin's own supplier-filter API endpoint.
 * An empty selection means that all suppliers are included.
 */

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
}

export function renderPluginSettings(target, data) {
    const api = data.api;
    const filterUrl = data.context?.supplier_filter_url ?? '/plugin/kicad-library-plugin/api/supplier-filter/';
    const enableSettingUrl = data.context?.enable_setting_url
        ?? '/api/plugins/kicad-library-plugin/settings/KICAD_ENABLE_MANUFACTURER_DATA/';

    let suppliers = [];
    let selected = new Set();
    let saveTimer = null;

    target.innerHTML = `
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
                style="flex: 1; padding: 6px 10px; border-radius: 4px;
                       border: 1px solid var(--mantine-color-default-border, #ccc);
                       background: var(--mantine-color-body, #fff);
                       color: var(--mantine-color-text, inherit);" />
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

    const searchInput = target.querySelector('[data-role="search"]');
    const listDiv = target.querySelector('[data-role="list"]');
    const selectedDiv = target.querySelector('[data-role="selected"]');
    const statusDiv = target.querySelector('[data-role="status"]');
    const clearButton = target.querySelector('[data-role="clear"]');
    const contentDiv = target.querySelector('[data-role="content"]');
    const disabledNote = target.querySelector('[data-role="disabled-note"]');

    function setEnabled(value) {
        const enabled = ['true', '1', 'yes', 'on'].includes(String(value).toLowerCase());
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
    // Instead, watch the shared API client for the request which saves the
    // "Add Manufacturer Data to KiCad Parts" setting, and update the visibility immediately.
    const interceptor = api.interceptors.response.use((response) => {
        if (!document.body.contains(target)) {
            // Panel has been closed - remove the interceptor
            api.interceptors.response.eject(interceptor);
        } else if (
            ['patch', 'put'].includes(response?.config?.method)
            && String(response?.config?.url ?? '').endsWith(enableSettingUrl)
        ) {
            if (setEnabled(response.data?.value)) {
                showNotification(
                    'Supplier selection available',
                    'You can now select specific suppliers in "Plugin Configuration" further down. '
                    + 'If no supplier is selected, data from all suppliers is added to KiCad parts.'
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
