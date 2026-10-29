/**
 * Custom settings panel for the KiCad Library plugin.
 *
 * Lets the user select which suppliers are included in the KiCad
 * manufacturer / supplier data. The selection is stored as a comma
 * separated list of company IDs in the plugin setting provided by the
 * server (KICAD_MANUFACTURER_DATA_SUPPLIERS). An empty selection means
 * that all suppliers are included.
 */

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text ?? '';
    return div.innerHTML;
}

function parseIds(value) {
    return new Set(
        String(value ?? '')
            .split(',')
            .map((x) => x.trim())
            .filter((x) => /^\d+$/.test(x))
            .map((x) => parseInt(x, 10))
    );
}

export function renderPluginSettings(target, data) {
    const api = data.api;
    const slug = data.context?.slug ?? 'kicad-library-plugin';
    const settingKey = data.context?.supplier_setting ?? 'KICAD_MANUFACTURER_DATA_SUPPLIERS';
    const settingUrl = `/api/plugins/${slug}/settings/${settingKey}/`;

    let suppliers = [];
    let selected = new Set();
    let saveTimer = null;

    target.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 8px;">
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
            const value = [...selected].sort((a, b) => a - b).join(',');
            setStatus('Saving...');
            api.patch(settingUrl, { value: value })
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

    Promise.all([
        api.get('/api/company/', { params: { is_supplier: true, ordering: 'name' } }),
        api.get(settingUrl)
    ])
        .then(([companyResponse, settingResponse]) => {
            const results = companyResponse.data?.results ?? companyResponse.data ?? [];
            suppliers = results.map((c) => ({ pk: c.pk, name: c.name }));
            selected = parseIds(settingResponse.data?.value);

            renderSelected();
            renderList();
            setStatus(`${suppliers.length} suppliers available`);
        })
        .catch((error) => setStatus(`Error loading suppliers: ${error?.message ?? error}`));
}
