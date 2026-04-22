async function api(endpoint, options = {}) {
    const response = await fetch(endpoint, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
        ...options,
    });

    if (response.status === 204) {
        return null;
    }

    let payload = null;
    try {
        payload = await response.json();
    } catch {
        payload = null;
    }

    if (!response.ok) {
        const message = payload && (payload.error || payload.details) ? (payload.error || payload.details) : `HTTP ${response.status}`;
        throw new Error(message);
    }

    return payload;
}

function initIndexPage() {
    const body = document.getElementById("productsTableBody");
    const search = document.getElementById("productSearch");
    const status = document.getElementById("productsStatus");
    if (!body || !search || !status) return;

    let products = [];

    function renderRows() {
        const query = (search.value || "").trim().toLowerCase();
        const filtered = products.filter((product) => {
            const name = String(product.name || "").toLowerCase();
            const description = String(product.beschreibung || "").toLowerCase();
            const supplier = String(product.lieferant || "").toLowerCase();
            const id = String(product.id || "").toLowerCase();
            return name.includes(query) || description.includes(query) || supplier.includes(query) || id.includes(query);
        });

        body.innerHTML = "";
        if (filtered.length === 0) {
            const row = document.createElement("tr");
            row.innerHTML = '<td colspan="8">Keine Produkte gefunden.</td>';
            body.appendChild(row);
            return;
        }

        filtered.forEach((product) => {
            const currency = product.waehrung || "EUR";
            const price = Number(product.preis ?? 0);
            const formattedPrice = Number.isFinite(price) ? `${price.toFixed(2)} ${currency}` : `0.00 ${currency}`;
            const params = new URLSearchParams(window.location.search);
            params.set("edit_product_id", String(product.id));
            const editHref = `/page1?${params.toString()}`;
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${product.id ?? ""}</td>
                <td>${product.name ?? ""}</td>
                <td>${product.beschreibung ?? ""}</td>
                <td>${product.lieferant || "Unbekannt"}</td>
                <td>${formattedPrice}</td>
                <td>${product.gewicht ?? ""}</td>
                <td>${product.einheit || "Stk"}</td>
                <td>
                    <div class="row-actions">
                        <a class="btn btn-small" href="${editHref}">Bearbeiten</a>
                        <button class="btn btn-small" type="button" data-id="${product.id}">Löschen</button>
                    </div>
                </td>
            `;
            body.appendChild(row);
        });
    }

    async function loadProducts() {
        status.textContent = "Lade Produkte ...";
        try {
            products = await api("/products");
            renderRows();
            status.textContent = `${products.length} Produkt(e) geladen.`;
        } catch (error) {
            status.textContent = `Fehler beim Laden: ${error.message}`;
        }
    }

    body.addEventListener("click", async (event) => {
        const target = event.target;
        if (!(target instanceof HTMLButtonElement)) return;
        const id = target.dataset.id;
        if (!id) return;

        const ok = confirm(`Produkt ${id} wirklich löschen?`);
        if (!ok) return;

        try {
            await api(`/products/${id}`, { method: "DELETE" });
            products = products.filter((product) => String(product.id) !== String(id));
            renderRows();
            status.textContent = `Produkt ${id} gelöscht.`;
        } catch (error) {
            status.textContent = `Fehler beim Löschen: ${error.message}`;
        }
    });

    search.addEventListener("input", renderRows);
    loadProducts();
}

function initProductPage() {
    const productSelect = document.getElementById("existingProduct");
    const warehouseStocks = document.getElementById("warehouseStocks");
    const nameInput = document.getElementById("productName");
    const priceInput = document.getElementById("productPrice");
    const currencyInput = document.getElementById("productCurrency");
    const supplierInput = document.getElementById("productSupplier");
    const descriptionInput = document.getElementById("productDescription");
    const weightInput = document.getElementById("productWeight");
    const unitInput = document.getElementById("productUnit");
    const status = document.getElementById("page1Status");
    const warehouseHint = document.getElementById("warehouseStocksHint");

    const saveBtn = document.getElementById("saveProductBtn");
    const discardBtn = document.getElementById("discardProductBtn");
    const deleteBtn = document.getElementById("deleteAttributeBtn");
    const addAttrBtn = document.getElementById("addAttributeBtn");

    if (!productSelect || !warehouseStocks || !warehouseHint || !nameInput || !priceInput || !currencyInput || !supplierInput || !descriptionInput || !weightInput || !unitInput || !status || !saveBtn || !discardBtn || !deleteBtn || !addAttrBtn) return;

    const title = document.querySelector(".product-title");
    const subtitle = document.querySelector(".product-subtitle");
    const requestedEditId = new URLSearchParams(window.location.search).get("edit_product_id");

    let products = [];
    let warehouses = [];
    let loadedInventory = new Map();

    function setStatus(message, kind = "info") {
        status.textContent = message;
        status.classList.remove("status-error");
        if (kind === "error") {
            status.classList.add("status-error");
        }
    }

    function markInvalidField(control, message) {
        if (!control) return;
        control.classList.add("is-invalid");
        control.setAttribute("aria-invalid", "true");
        if (message) control.title = message;
        const row = control.closest(".field-row");
        if (row) row.classList.add("is-invalid");
    }

    function clearInvalidField(control) {
        if (!control) return;
        control.classList.remove("is-invalid");
        control.removeAttribute("aria-invalid");
        control.removeAttribute("title");
        const row = control.closest(".field-row");
        if (row) row.classList.remove("is-invalid");
    }

    function clearRequiredHighlights() {
        clearInvalidField(nameInput);
        clearInvalidField(priceInput);
        clearInvalidField(weightInput);
    }

    function validateRequiredFields(payload) {
        clearRequiredHighlights();
        const invalid = [];

        if (!payload.name) {
            markInvalidField(nameInput, "Bitte einen Produktnamen eingeben.");
            invalid.push(nameInput);
        }

        if (Number.isNaN(payload.preis) || payload.preis < 0) {
            markInvalidField(priceInput, "Bitte einen gültigen Preis (>= 0) eingeben.");
            invalid.push(priceInput);
        }

        if (Number.isNaN(payload.gewicht) || payload.gewicht <= 0) {
            markInvalidField(weightInput, "Bitte eine gültige Menge (> 0) eingeben.");
            invalid.push(weightInput);
        }

        if (invalid.length) {
            invalid[0].focus();
            return false;
        }

        return true;
    }

    function setHeader(productId) {
        if (!title || !subtitle) return;
        if (!productId) {
            title.textContent = "Neues Produkt";
            subtitle.textContent = "Neues Produkt erstellen";
            return;
        }
        title.textContent = "Produkt bearbeiten";
        subtitle.textContent = `Produkt ${productId} bearbeiten`;
    }

    function clearForm() {
        nameInput.value = "";
        priceInput.value = "";
        currencyInput.value = "EUR";
        supplierInput.value = "";
        descriptionInput.value = "";
        weightInput.value = "";
        unitInput.value = "Stk";
        for (const input of warehouseStocks.querySelectorAll("input[data-warehouse-id]")) {
            input.value = "0";
        }
        loadedInventory = new Map();
        setHeader("");
        clearRequiredHighlights();
    }

    function ensureCurrencyOption(code) {
        const normalized = String(code || "").trim().toUpperCase();
        if (!normalized) return;
        const hasOption = Array.from(currencyInput.options).some((opt) => String(opt.value).toUpperCase() === normalized);
        if (hasOption) return;

        const option = document.createElement("option");
        option.value = normalized;
        option.textContent = `${normalized} — (unbekannt)`;
        currencyInput.appendChild(option);
    }

    function ensureUnitOption(unit) {
        const normalized = String(unit || "").trim();
        if (!normalized) return;
        const hasOption = Array.from(unitInput.options).some((opt) => String(opt.value) === normalized);
        if (hasOption) return;

        const option = document.createElement("option");
        option.value = normalized;
        option.textContent = `${normalized} — (unbekannt)`;
        unitInput.appendChild(option);
    }

    function productPayload() {
        return {
            name: nameInput.value.trim(),
            preis: Number(priceInput.value || 0),
            waehrung: currencyInput.value || "EUR",
            lieferant: supplierInput.value.trim(),
            beschreibung: descriptionInput.value.trim(),
            gewicht: Number(weightInput.value),
            einheit: unitInput.value || "Stk",
        };
    }

    function fillProductForm(productId) {
        const product = products.find((item) => String(item.id) === String(productId));
        if (!product) {
            clearForm();
            return;
        }
        nameInput.value = product.name || "";
        priceInput.value = product.preis ?? "";
        ensureCurrencyOption(product.waehrung);
        currencyInput.value = product.waehrung || "EUR";
        supplierInput.value = product.lieferant || "";
        descriptionInput.value = product.beschreibung || "";
        weightInput.value = product.gewicht ?? "";
        ensureUnitOption(product.einheit);
        unitInput.value = product.einheit || "Stk";
        setHeader(productId);
        clearRequiredHighlights();
    }

    function renderProductOptions() {
        const current = productSelect.value;
        productSelect.innerHTML = '<option value="">Neues Produkt</option>';
        products.forEach((product) => {
            const option = document.createElement("option");
            option.value = String(product.id);
            option.textContent = `${product.id} - ${product.name}`;
            productSelect.appendChild(option);
        });

        if (current && products.some((product) => String(product.id) === current)) {
            productSelect.value = current;
        } else {
            productSelect.value = "";
        }
    }

    function renderWarehouseStocks() {
        warehouseStocks.innerHTML = "";
        if (!warehouses.length) {
            warehouseStocks.innerHTML = '<div class="warehouse-name">Keine Lager vorhanden.</div>';
            warehouseHint.textContent = "Kein Lager vorhanden – bitte zuerst ein Lager in 'Lagerliste' anlegen.";
            warehouseHint.classList.add("is-error");
            return;
        }

        warehouseHint.textContent = "Mengen-Eintrag 0 bedeutet: kein Bestand in diesem Lager.";
        warehouseHint.classList.remove("is-error");
        warehouses.forEach((warehouse) => {
            const row = document.createElement("div");
            row.className = "warehouse-row";
            row.innerHTML = `
                <div class="warehouse-name">${warehouse.lagername ?? ""}</div>
                <input type="number" min="0" step="1" value="0" inputmode="numeric" data-warehouse-id="${warehouse.id}" aria-label="Menge für ${warehouse.lagername ?? "Lager"}" />
            `;
            warehouseStocks.appendChild(row);
        });
    }

    async function loadProducts() {
        products = await api("/products");
        renderProductOptions();
    }

    async function loadWarehouses() {
        warehouses = await api("/warehouses");
        renderWarehouseStocks();
    }

    async function loadInventoryForProduct(productId) {
        loadedInventory = new Map();
        for (const input of warehouseStocks.querySelectorAll("input[data-warehouse-id]")) {
            input.value = "0";
        }
        if (!productId) return;
        const rows = await api(`/inventory/products/${productId}`);
        rows.forEach((row) => {
            loadedInventory.set(String(row.lager_id), Number(row.menge));
        });
        for (const input of warehouseStocks.querySelectorAll("input[data-warehouse-id]")) {
            const wid = String(input.dataset.warehouseId);
            if (loadedInventory.has(wid)) {
                input.value = String(loadedInventory.get(wid));
            }
        }
    }

    async function createOrUpdateProduct() {
        const payload = productPayload();
        if (!validateRequiredFields(payload)) {
            throw new Error("Name, Menge und ein gültiger Preis sind Pflichtfelder.");
        }

        const existingId = productSelect.value;
        if (!existingId) {
            const created = await api("/products", {
                method: "POST",
                body: JSON.stringify(payload),
            });
            await loadProducts();
            productSelect.value = String(created.id);
            fillProductForm(created.id);
            setStatus(`Produkt ${created.id} erstellt.`);
            return String(created.id);
        }

        await api(`/products/${existingId}`, {
            method: "PUT",
            body: JSON.stringify(payload),
        });
        await loadProducts();
        productSelect.value = String(existingId);
        fillProductForm(existingId);
        setStatus(`Produkt ${existingId} aktualisiert.`);
        return String(existingId);
    }

    async function saveInventoryForProduct(productId) {
        const ops = [];
        for (const input of warehouseStocks.querySelectorAll("input[data-warehouse-id]")) {
            const warehouseId = String(input.dataset.warehouseId);
            const qty = Number(input.value);
            if (Number.isNaN(qty) || qty < 0) {
                throw new Error("Bestand darf nicht negativ sein.");
            }
            if (qty > 0) {
                ops.push(
                    api("/inventory", {
                        method: "PUT",
                        body: JSON.stringify({ lager_id: Number(warehouseId), produkt_id: Number(productId), menge: qty }),
                    })
                );
            } else if (loadedInventory.has(warehouseId)) {
                ops.push(api(`/inventory/${warehouseId}/${productId}`, { method: "DELETE" }));
            }
        }
        await Promise.all(ops);
        await loadInventoryForProduct(productId);
    }

    async function saveAll() {
        const productId = await createOrUpdateProduct();
        await saveInventoryForProduct(productId);
        setStatus(`Produkt ${productId} gespeichert.`);
    }

    async function deleteProduct() {
        const productId = productSelect.value;
        if (!productId) throw new Error("Bitte zuerst ein Produkt auswählen.");
        if (!confirm(`Produkt ${productId} löschen?`)) return;
        await api(`/products/${productId}`, { method: "DELETE" });
        await loadProducts();
        productSelect.value = "";
        clearForm();
        setStatus(`Produkt ${productId} gelöscht.`);
    }

    async function discardChanges() {
        const productId = productSelect.value;
        fillProductForm(productId);
        await loadInventoryForProduct(productId);
        setStatus(productId ? "Änderungen verworfen." : "Zurückgesetzt.");
    }

    function bind(button, action) {
        button.addEventListener("click", async () => {
            try {
                await action();
            } catch (error) {
                setStatus(`Fehler: ${error.message}`, "error");
            }
        });
    }

    productSelect.addEventListener("change", async () => {
        const productId = productSelect.value;
        fillProductForm(productId);
        clearRequiredHighlights();
        try {
            await loadInventoryForProduct(productId);
        } catch (error) {
            setStatus(`Fehler beim Laden des Bestands: ${error.message}`, "error");
        }
    });

    [nameInput, priceInput, weightInput].forEach((control) => {
        control.addEventListener("input", () => clearInvalidField(control));
        control.addEventListener("change", () => clearInvalidField(control));
    });

    bind(saveBtn, saveAll);
    bind(discardBtn, discardChanges);
    bind(deleteBtn, deleteProduct);
    addAttrBtn.addEventListener("click", () => {
        status.textContent = "Attribut-Management ist noch nicht implementiert.";
    });

    (async function init() {
        try {
            setStatus("Lade Produkt- und Lagerdaten ...");
            await Promise.all([loadProducts(), loadWarehouses()]);
            if (requestedEditId && products.some((product) => String(product.id) === String(requestedEditId))) {
                productSelect.value = String(requestedEditId);
            }
            fillProductForm(productSelect.value);
            await loadInventoryForProduct(productSelect.value);
            setStatus("Bereit.");
        } catch (error) {
            setStatus(`Initialisierung fehlgeschlagen: ${error.message}`, "error");
        }
    })();
}

function initWarehousePage() {
    const body = document.getElementById("warehousesTableBody");
    const status = document.getElementById("warehousesStatus");
    const createBtn = document.getElementById("createWarehouseBtn");
    const searchInput = document.getElementById("warehouseSearch");
    const nameInput = document.getElementById("warehouseName");
    const addressInput = document.getElementById("warehouseAddress");
    const capacityInput = document.getElementById("warehouseCapacity");

    if (!body || !status || !createBtn || !searchInput || !nameInput || !addressInput || !capacityInput) return;

    let warehouses = [];

    function filteredWarehouses() {
        const query = String(searchInput.value || "").trim().toLowerCase();
        if (!query) return warehouses;
        return warehouses.filter((warehouse) => {
            const haystack = [
                warehouse.id,
                warehouse.lagername,
                warehouse.adresse,
                warehouse.firma_id,
                warehouse.max_plaetze,
            ]
                .map((v) => String(v ?? "").toLowerCase())
                .join(" | ");
            return haystack.includes(query);
        });
    }

    function renderRows() {
        const visibleWarehouses = filteredWarehouses();
        body.innerHTML = "";
        if (!visibleWarehouses.length) {
            const row = document.createElement("tr");
            row.innerHTML = '<td colspan="7">Keine Lager zur Suche gefunden.</td>';
            body.appendChild(row);
            return;
        }

        visibleWarehouses.forEach((warehouse) => {
            const products = Number(warehouse.products || 0);
            const capacity = Number(warehouse.max_plaetze || 0);
            const utilization = capacity > 0 ? Math.round((products / capacity) * 100) : 0;
            const row = document.createElement("tr");
            row.dataset.id = String(warehouse.id);
            row.innerHTML = `
                <td>${warehouse.lagername ?? ""}</td>
                <td><span class="pill">${warehouse.id ?? ""}</span></td>
                <td>${warehouse.adresse ?? ""}</td>
                <td><span class="pill">${products} Produkte</span></td>
                <td><span class="pill">${capacity} max.</span></td>
                <td><span class="pill">${utilization}%</span></td>
                <td class="actions">
                    <button class="btn btn-small" type="button" data-open-id="${warehouse.id}">Produkte</button>
                    <button class="btn btn-small" type="button" data-delete-id="${warehouse.id}">Löschen</button>
                </td>
            `;
            body.appendChild(row);
        });
    }

    function selectedThemeQuery() {
        const params = new URLSearchParams(window.location.search);
        const theme = params.get("theme");
        return theme ? `&theme=${encodeURIComponent(theme)}` : "";
    }

    function openWarehouseDetail(id) {
        window.location.href = `/page5?warehouse_id=${encodeURIComponent(id)}${selectedThemeQuery()}`;
    }

    async function loadWarehouses() {
        status.textContent = "Lade Lager ...";
        warehouses = await api("/warehouses");
        renderRows();
        const visibleCount = filteredWarehouses().length;
        status.textContent = `${visibleCount} von ${warehouses.length} Lager(n) angezeigt.`;
    }

    async function createWarehouse() {
        const payload = {
            lagername: nameInput.value.trim(),
            adresse: addressInput.value.trim(),
            max_plaetze: Number(capacityInput.value),
        };
        if (!payload.lagername || !payload.adresse || !payload.max_plaetze) {
            throw new Error("Bitte alle Felder für das Lager ausfüllen.");
        }

        await api("/warehouses", {
            method: "POST",
            body: JSON.stringify(payload),
        });

        nameInput.value = "";
        addressInput.value = "";
        capacityInput.value = "";
        await loadWarehouses();
        status.textContent = "Lager erstellt.";
    }

    async function deleteWarehouse(id) {
        await api(`/warehouses/${id}`, { method: "DELETE" });
        await loadWarehouses();
        status.textContent = `Lager ${id} gelöscht.`;
    }

    createBtn.addEventListener("click", async () => {
        try {
            await createWarehouse();
        } catch (error) {
            status.textContent = `Fehler: ${error.message}`;
        }
    });

    searchInput.addEventListener("input", () => {
        renderRows();
        const visibleCount = filteredWarehouses().length;
        status.textContent = `${visibleCount} von ${warehouses.length} Lager(n) angezeigt.`;
    });

    body.addEventListener("click", async (event) => {
        const target = event.target;
        if (target instanceof HTMLButtonElement) {
            const openId = target.dataset.openId;
            if (openId) {
                openWarehouseDetail(openId);
                return;
            }

            const deleteId = target.dataset.deleteId;
            if (deleteId) {
                if (!confirm(`Lager ${deleteId} wirklich löschen?`)) return;
                try {
                    await deleteWarehouse(deleteId);
                } catch (error) {
                    status.textContent = `Fehler: ${error.message}`;
                }
            }
            return;
        }
    });

    loadWarehouses().catch((error) => {
        status.textContent = `Fehler beim Laden: ${error.message}`;
    });
}

function initWarehouseDetailPage() {
    const body = document.getElementById("warehouseDetailTableBody");
    const status = document.getElementById("warehouseDetailStatus");
    const title = document.getElementById("warehouseDetailTitle");
    const subtitle = document.getElementById("warehouseDetailSubtitle");
    const backLink = document.getElementById("backToWarehouseList");
    const warehouseNameInput = document.getElementById("warehouseNameEdit");
    const saveWarehouseNameBtn = document.getElementById("saveWarehouseNameBtn");
    const addProductSelect = document.getElementById("addProductSelect");
    const addProductQty = document.getElementById("addProductQty");
    const addProductBtn = document.getElementById("addProductToWarehouseBtn");

    if (!body || !status || !title || !subtitle || !backLink || !warehouseNameInput || !saveWarehouseNameBtn || !addProductSelect || !addProductQty || !addProductBtn) return;

    const params = new URLSearchParams(window.location.search);
    const warehouseId = params.get("warehouse_id");
    const selectedTheme = params.get("theme");

    if (selectedTheme) {
        backLink.href = `/page2?theme=${encodeURIComponent(selectedTheme)}`;
    }

    if (!warehouseId) {
        status.textContent = "Bitte ein Lager aus der Lagerliste auswählen.";
        body.innerHTML = '<tr><td colspan="5">Keine Lager-ID übergeben.</td></tr>';
        return;
    }

    let productsById = new Map();
    let products = [];
    let warehouses = [];
    let inventoryRows = [];

    function renderAddProductOptions() {
        const inStockIds = new Set(inventoryRows.map((row) => String(row.produkt_id)));
        addProductSelect.innerHTML = '<option value="">Produkt wählen</option>';

        products.forEach((product) => {
            if (inStockIds.has(String(product.id))) return;
            const option = document.createElement("option");
            option.value = String(product.id);
            option.textContent = `${product.id} - ${product.name || `Produkt ${product.id}`}`;
            addProductSelect.appendChild(option);
        });
    }

    function renderTable() {
        body.innerHTML = "";

        if (!inventoryRows.length) {
            body.innerHTML = '<tr><td colspan="5">In diesem Lager sind aktuell keine Produkte.</td></tr>';
            return;
        }

        const targetWarehouses = warehouses.filter((w) => String(w.id) !== String(warehouseId));

        inventoryRows.forEach((row) => {
            const productId = String(row.produkt_id);
            const quantity = Number(row.menge || 0);
            const productName = productsById.get(productId) || `Produkt ${productId}`;

            const tr = document.createElement("tr");
            tr.dataset.productId = productId;
            tr.innerHTML = `
                <td>${productId}</td>
                <td>${productName}</td>
                <td>
                    <div class="detail-inline-actions">
                        <input type="number" min="0" step="1" value="${quantity}" data-edit-qty="${productId}" aria-label="Neue Menge für Produkt ${productId}" />
                        <button class="btn btn-small" type="button" data-action="edit" data-product-id="${productId}">Speichern</button>
                    </div>
                </td>
                <td>
                    <div class="detail-inline-actions detail-move-actions">
                        <input type="number" min="1" max="${quantity}" step="1" value="1" data-move-qty="${productId}" aria-label="Menge verschieben für Produkt ${productId}" />
                        <select data-target-warehouse="${productId}" aria-label="Ziellager für Produkt ${productId}">
                            <option value="">Ziellager wählen</option>
                            ${targetWarehouses
                                .map((w) => `<option value="${w.id}">${w.lagername ?? `Lager ${w.id}`}</option>`)
                                .join("")}
                        </select>
                        <button class="btn btn-small" type="button" data-action="move" data-product-id="${productId}">Verschieben</button>
                    </div>
                </td>
                <td>
                    <button class="btn btn-small btn-danger" type="button" data-action="remove" data-product-id="${productId}">Entfernen</button>
                </td>
            `;
            body.appendChild(tr);
        });
    }

    async function refresh() {
        const [warehousesData, productsData, inventoryData] = await Promise.all([
            api("/warehouses"),
            api("/products"),
            api(`/inventory/${warehouseId}/products`),
        ]);

        warehouses = warehousesData;
        products = productsData;
        productsById = new Map(productsData.map((p) => [String(p.id), p.name || `Produkt ${p.id}`]));
        inventoryRows = inventoryData;

        const currentWarehouse = warehouses.find((w) => String(w.id) === String(warehouseId));
        const warehouseName = currentWarehouse?.lagername || `Lager ${warehouseId}`;
        title.textContent = `${warehouseName} (ID ${warehouseId})`;
        warehouseNameInput.value = currentWarehouse?.lagername || "";
        subtitle.textContent = currentWarehouse
            ? `${currentWarehouse.adresse || "Ohne Adresse"} - Produkte im Lager verwalten`
            : "Produkte im Lager verwalten";

        renderTable();
        renderAddProductOptions();
        status.textContent = `${inventoryRows.length} Produktposition(en) geladen.`;
    }

    body.addEventListener("click", async (event) => {
        const target = event.target;
        if (!(target instanceof HTMLButtonElement)) return;

        const action = target.dataset.action;
        const productId = target.dataset.productId;
        if (!action || !productId) return;

        try {
            if (action === "remove") {
                if (!confirm(`Produkt ${productId} aus Lager ${warehouseId} entfernen?`)) return;
                await api(`/inventory/${warehouseId}/${productId}`, { method: "DELETE" });
                await refresh();
                status.textContent = `Produkt ${productId} entfernt.`;
                return;
            }

            if (action === "edit") {
                const qtyInput = body.querySelector(`input[data-edit-qty="${productId}"]`);
                const newQty = Number(qtyInput?.value);
                if (!Number.isInteger(newQty) || newQty < 0) {
                    throw new Error("Menge muss eine ganze Zahl >= 0 sein.");
                }

                await api("/inventory", {
                    method: "PUT",
                    body: JSON.stringify({ lager_id: Number(warehouseId), produkt_id: Number(productId), menge: newQty }),
                });
                await refresh();
                status.textContent = `Menge für Produkt ${productId} aktualisiert.`;
                return;
            }

            if (action === "move") {
                const qtyInput = body.querySelector(`input[data-move-qty="${productId}"]`);
                const targetSelect = body.querySelector(`select[data-target-warehouse="${productId}"]`);
                const moveQty = Number(qtyInput?.value);
                const targetWarehouseId = targetSelect?.value;

                if (!targetWarehouseId) {
                    throw new Error("Bitte ein Ziellager auswählen.");
                }
                if (!Number.isInteger(moveQty) || moveQty <= 0) {
                    throw new Error("Verschiebemenge muss eine ganze Zahl > 0 sein.");
                }

                await api("/inventory/move", {
                    method: "POST",
                    body: JSON.stringify({
                        source_lager_id: Number(warehouseId),
                        target_lager_id: Number(targetWarehouseId),
                        produkt_id: Number(productId),
                        menge: moveQty,
                    }),
                });

                await refresh();
                status.textContent = `Produkt ${productId} nach Lager ${targetWarehouseId} verschoben.`;
            }
        } catch (error) {
            status.textContent = `Fehler: ${error.message}`;
        }
    });

    saveWarehouseNameBtn.addEventListener("click", async () => {
        const nextName = String(warehouseNameInput.value || "").trim();
        if (!nextName) {
            status.textContent = "Fehler: Lagername darf nicht leer sein.";
            return;
        }

        try {
            await api(`/warehouses/${warehouseId}`, {
                method: "PUT",
                body: JSON.stringify({ lagername: nextName }),
            });
            await refresh();
            status.textContent = "Lagername gespeichert.";
        } catch (error) {
            status.textContent = `Fehler: ${error.message}`;
        }
    });

    addProductBtn.addEventListener("click", async () => {
        const productId = addProductSelect.value;
        const qty = Number(addProductQty.value);

        if (!productId) {
            status.textContent = "Fehler: Bitte ein Produkt auswählen.";
            return;
        }
        if (!Number.isInteger(qty) || qty <= 0) {
            status.textContent = "Fehler: Menge muss eine ganze Zahl > 0 sein.";
            return;
        }

        try {
            await api("/inventory", {
                method: "PUT",
                body: JSON.stringify({ lager_id: Number(warehouseId), produkt_id: Number(productId), menge: qty }),
            });
            addProductQty.value = "1";
            addProductSelect.value = "";
            await refresh();
            status.textContent = `Produkt ${productId} hinzugefügt.`;
        } catch (error) {
            status.textContent = `Fehler: ${error.message}`;
        }
    });

    refresh().catch((error) => {
        status.textContent = `Fehler beim Laden: ${error.message}`;
        body.innerHTML = '<tr><td colspan="5">Lagerdaten konnten nicht geladen werden.</td></tr>';
    });
}

function initStatsPage() {
    const warehousesValue = document.getElementById("kpiWarehouses");
    const productsValue = document.getElementById("kpiProducts");
    const capacityValue = document.getElementById("kpiCapacity");
    const freeCapacityValue = document.getElementById("kpiFreeCapacity");
    const topProductValue = document.getElementById("kpiTopProduct");
    const topProductSub = document.getElementById("kpiTopProductSub");
    const maxUtilValue = document.getElementById("kpiMaxUtil");
    const maxUtilSub = document.getElementById("kpiMaxUtilSub");
    const avgUtilValue = document.getElementById("kpiAvgUtil");
    const activeWarehousesValue = document.getElementById("kpiActiveWarehouses");
    const inventoryValueKpi = document.getElementById("kpiInventoryValue");
    const mainCurrencyKpi = document.getElementById("kpiMainCurrency");
    const topSupplierKpi = document.getElementById("kpiTopSupplier");
    const topSupplierSub = document.getElementById("kpiTopSupplierSub");
    const chartHost = document.getElementById("chartWarehouses");
    const utilHost = document.getElementById("chartUtilization");
    const distributionHost = document.getElementById("chartDistribution");
    const currencyHost = document.getElementById("chartCurrencyValue");
    const topHost = document.getElementById("topProducts");
    const unitMixHost = document.getElementById("unitMixList");
    const supplierMixHost = document.getElementById("supplierMixList");

    if (!warehousesValue || !productsValue || !capacityValue || !freeCapacityValue || !topProductValue || !topProductSub || !maxUtilValue || !maxUtilSub || !avgUtilValue || !activeWarehousesValue || !inventoryValueKpi || !mainCurrencyKpi || !topSupplierKpi || !topSupplierSub || !chartHost || !utilHost || !distributionHost || !currencyHost || !topHost || !unitMixHost || !supplierMixHost) return;

    (async function run() {
        try {
            const [warehouses, products] = await Promise.all([api("/warehouses"), api("/products")]);
            const productMap = new Map(products.map((product) => [String(product.id), product.name || `Produkt ${product.id}`]));
            const productMeta = new Map(
                products.map((product) => [
                    String(product.id),
                    {
                        preis: Number(product.preis || 0),
                        waehrung: product.waehrung || "EUR",
                        lieferant: product.lieferant || "Unbekannt",
                        einheit: product.einheit || "Stk",
                    },
                ])
            );
            const inventoryByWarehouse = [];
            const productTotals = new Map();
            const currencyTotals = new Map();
            const unitTotals = new Map();
            const supplierTotals = new Map();

            for (const warehouse of warehouses) {
                const items = await api(`/inventory/${warehouse.id}/products`);
                const totalProducts = items.reduce((sum, item) => sum + Number(item.menge || 0), 0);
                inventoryByWarehouse.push({
                    name: warehouse.lagername,
                    products: totalProducts,
                    capacity: Number(warehouse.max_plaetze || 0),
                });

                items.forEach((item) => {
                    const productId = String(item.produkt_id);
                    const qty = Number(item.menge || 0);
                    const current = productTotals.get(productId) || 0;
                    productTotals.set(productId, current + qty);

                    const meta = productMeta.get(productId) || { preis: 0, waehrung: "EUR", einheit: "Stk" };
                    const currencyValue = (currencyTotals.get(meta.waehrung) || 0) + meta.preis * qty;
                    currencyTotals.set(meta.waehrung, currencyValue);

                    const unitValue = (unitTotals.get(meta.einheit) || 0) + qty;
                    unitTotals.set(meta.einheit, unitValue);

                    const supplierValue = (supplierTotals.get(meta.lieferant) || 0) + qty;
                    supplierTotals.set(meta.lieferant, supplierValue);
                });
            }

            const topProducts = Array.from(productTotals.entries())
                .map(([id, qty]) => ({ name: productMap.get(id) || `Produkt ${id}`, qty }))
                .sort((a, b) => b.qty - a.qty);

            const totalWarehouses = warehouses.length;
            const totalProducts = inventoryByWarehouse.reduce((sum, item) => sum + item.products, 0);
            const totalCapacity = inventoryByWarehouse.reduce((sum, item) => sum + item.capacity, 0);
            const freeCapacity = Math.max(0, totalCapacity - totalProducts);
            const topProduct = topProducts[0] || null;
            const byUtil = inventoryByWarehouse
                .map((item) => ({ ...item, util: item.capacity > 0 ? item.products / item.capacity : 0 }))
                .sort((a, b) => b.util - a.util);
            const maxUtil = byUtil[0] || null;
            const avgUtil = totalWarehouses > 0 ? byUtil.reduce((sum, item) => sum + item.util, 0) / totalWarehouses : 0;
            const activeWarehouses = inventoryByWarehouse.filter((item) => item.products > 0).length;
            const currencyEntries = Array.from(currencyTotals.entries()).sort((a, b) => b[1] - a[1]);
            const totalInventoryValue = currencyEntries.reduce((sum, [, value]) => sum + value, 0);
            const mainCurrency = currencyEntries[0]?.[0] || "-";
            const supplierEntries = Array.from(supplierTotals.entries()).sort((a, b) => b[1] - a[1]);
            const topSupplier = supplierEntries[0] || null;

            warehousesValue.textContent = String(totalWarehouses);
            productsValue.textContent = String(totalProducts);
            capacityValue.textContent = String(totalCapacity);
            freeCapacityValue.textContent = String(freeCapacity);
            topProductValue.textContent = topProduct ? topProduct.name : "-";
            topProductSub.textContent = topProduct ? `${topProduct.qty} Stk.` : "-";
            avgUtilValue.textContent = `${Math.round(avgUtil * 100)}%`;
            activeWarehousesValue.textContent = `${activeWarehouses}/${totalWarehouses}`;
            inventoryValueKpi.textContent = `${totalInventoryValue.toFixed(2)}${currencyEntries.length === 1 ? ` ${mainCurrency}` : ""}`;
            mainCurrencyKpi.textContent = currencyEntries.length <= 1 ? mainCurrency : `${mainCurrency} (gemischt)`;
            topSupplierKpi.textContent = topSupplier ? topSupplier[0] : "-";
            topSupplierSub.textContent = topSupplier ? `${topSupplier[1]} Stück im Bestand` : "-";

            if (maxUtil) {
                const pct = Math.round(maxUtil.util * 100);
                maxUtilValue.textContent = `${pct}%`;
                maxUtilSub.textContent = `${maxUtil.name} (${maxUtil.products}/${maxUtil.capacity})`;
            } else {
                maxUtilValue.textContent = "-";
                maxUtilSub.textContent = "-";
            }

            chartHost.innerHTML = "";
            const maxProducts = Math.max(1, ...inventoryByWarehouse.map((item) => item.products));
            inventoryByWarehouse
                .slice()
                .sort((a, b) => b.products - a.products)
                .forEach((item) => {
                    const row = document.createElement("div");
                    row.className = "bar-row";

                    const label = document.createElement("div");
                    label.className = "bar-label";
                    label.textContent = item.name;

                    const track = document.createElement("div");
                    track.className = "bar-track";

                    const fill = document.createElement("div");
                    fill.className = "bar-fill";
                    fill.style.width = `${Math.round((item.products / maxProducts) * 100)}%`;

                    const value = document.createElement("div");
                    value.className = "bar-value";
                    value.textContent = `${item.products} Stk.`;

                    track.appendChild(fill);
                    row.appendChild(label);
                    row.appendChild(track);
                    row.appendChild(value);
                    chartHost.appendChild(row);
                });

            topHost.innerHTML = "";
            topProducts.slice(0, 5).forEach((item) => {
                const li = document.createElement("li");
                li.className = "list-item";

                const title = document.createElement("strong");
                title.textContent = item.name;

                const pill = document.createElement("span");
                pill.className = "pill";
                pill.textContent = `${item.qty} Stk.`;

                li.appendChild(title);
                li.appendChild(pill);
                topHost.appendChild(li);
            });

            utilHost.innerHTML = "";
            byUtil.forEach((item) => {
                const row = document.createElement("div");
                row.className = "bar-row";

                const label = document.createElement("div");
                label.className = "bar-label";
                label.textContent = item.name;

                const track = document.createElement("div");
                track.className = "bar-track";

                const fill = document.createElement("div");
                fill.className = "bar-fill";
                fill.style.width = `${Math.round(item.util * 100)}%`;

                const value = document.createElement("div");
                value.className = "bar-value";
                value.textContent = `${Math.round(item.util * 100)}%`;

                track.appendChild(fill);
                row.appendChild(label);
                row.appendChild(track);
                row.appendChild(value);
                utilHost.appendChild(row);
            });

            distributionHost.innerHTML = "";
            const usedPercent = totalCapacity > 0 ? Math.round((totalProducts / totalCapacity) * 100) : 0;
            const freePercent = Math.max(0, 100 - usedPercent);

            const donutWrap = document.createElement("div");
            donutWrap.className = "donut-wrap";

            const donut = document.createElement("div");
            donut.className = "donut-chart";
            donut.style.background = `conic-gradient(var(--fg) 0% ${usedPercent}%, var(--surface-2) ${usedPercent}% 100%)`;
            donut.innerHTML = `<span>${usedPercent}%</span>`;

            const legend = document.createElement("ul");
            legend.className = "legend-list";
            legend.innerHTML = `
                <li><span class="dot used"></span>Belegt: ${totalProducts} (${usedPercent}%)</li>
                <li><span class="dot free"></span>Frei: ${freeCapacity} (${freePercent}%)</li>
            `;

            donutWrap.appendChild(donut);
            donutWrap.appendChild(legend);
            distributionHost.appendChild(donutWrap);

            currencyHost.innerHTML = "";
            const maxCurrencyValue = Math.max(1, ...currencyEntries.map((entry) => entry[1]));
            currencyEntries.forEach(([currency, value]) => {
                const row = document.createElement("div");
                row.className = "bar-row";

                const label = document.createElement("div");
                label.className = "bar-label";
                label.textContent = currency;

                const track = document.createElement("div");
                track.className = "bar-track";

                const fill = document.createElement("div");
                fill.className = "bar-fill";
                fill.style.width = `${Math.round((value / maxCurrencyValue) * 100)}%`;

                const valueNode = document.createElement("div");
                valueNode.className = "bar-value";
                valueNode.textContent = `${value.toFixed(2)} ${currency}`;

                track.appendChild(fill);
                row.appendChild(label);
                row.appendChild(track);
                row.appendChild(valueNode);
                currencyHost.appendChild(row);
            });

            unitMixHost.innerHTML = "";
            const unitEntries = Array.from(unitTotals.entries()).sort((a, b) => b[1] - a[1]);
            unitEntries.forEach(([unit, qty]) => {
                const li = document.createElement("li");
                li.className = "list-item";

                const title = document.createElement("strong");
                title.textContent = unit;

                const pill = document.createElement("span");
                pill.className = "pill";
                pill.textContent = `${qty} ${unit}`;

                li.appendChild(title);
                li.appendChild(pill);
                unitMixHost.appendChild(li);
            });

            supplierMixHost.innerHTML = "";
            supplierEntries.slice(0, 10).forEach(([supplier, qty]) => {
                const li = document.createElement("li");
                li.className = "list-item";

                const title = document.createElement("strong");
                title.textContent = supplier;

                const pill = document.createElement("span");
                pill.className = "pill";
                pill.textContent = `${qty} Stück`;

                li.appendChild(title);
                li.appendChild(pill);
                supplierMixHost.appendChild(li);
            });
        } catch (error) {
            warehousesValue.textContent = "!";
            productsValue.textContent = "!";
            capacityValue.textContent = "!";
            freeCapacityValue.textContent = "!";
            topProductValue.textContent = "Fehler";
            topProductSub.textContent = error.message;
            maxUtilValue.textContent = "!";
            maxUtilSub.textContent = error.message;
            avgUtilValue.textContent = "!";
            activeWarehousesValue.textContent = "!";
            inventoryValueKpi.textContent = "!";
            mainCurrencyKpi.textContent = "!";
            topSupplierKpi.textContent = "!";
            topSupplierSub.textContent = error.message;
        }
    })();
}

function initHistoryPage() {
    const body = document.getElementById("historyTableBody");
    const status = document.getElementById("historyStatus");
    const typeSelect = document.getElementById("historyType");
    const searchInput = document.getElementById("historySearch");
    const sortSelect = document.getElementById("historySort");
    const exportBtn = document.getElementById("exportHistoryTxtBtn");

    if (!body || !status || !typeSelect || !searchInput || !sortSelect || !exportBtn) return;

    let entries = [];

    function typeLabel(type) {
        if (type === "product") return "Produkt";
        if (type === "warehouse") return "Lager";
        if (type === "inventory") return "Bestand";
        return type || "–";
    }

    function actionLabel(action) {
        if (action === "create") return "Erstellt";
        if (action === "update") return "Aktualisiert";
        if (action === "delete") return "Gelöscht";
        if (action === "assign") return "Gebucht";
        if (action === "add") return "Hinzugefügt";
        return action || "–";
    }

    function parseDate(value) {
        if (!value) return null;
        const d = new Date(value);
        return isNaN(d.getTime()) ? null : d;
    }

    function formatDate(value) {
        const d = parseDate(value);
        if (!d) return "–";
        return d.toLocaleString("de-AT");
    }

    function filteredAndSorted() {
        const typeFilter = String(typeSelect.value || "all");
        const query = String(searchInput.value || "").trim().toLowerCase();
        const sort = String(sortSelect.value || "desc");

        let result = entries.slice();

        if (typeFilter !== "all") {
            result = result.filter((e) => String(e.entry_type) === typeFilter);
        }

        if (query) {
            result = result.filter((e) => {
                const hay = [
                    e.created_at,
                    e.entry_type,
                    e.action,
                    e.details,
                    typeLabel(e.entry_type),
                    actionLabel(e.action),
                ]
                    .map((v) => String(v || "").toLowerCase())
                    .join(" | ");
                return hay.includes(query);
            });
        }

        result.sort((a, b) => {
            const da = parseDate(a.created_at);
            const db = parseDate(b.created_at);
            const ta = da ? da.getTime() : 0;
            const tb = db ? db.getTime() : 0;
            return sort === "asc" ? ta - tb : tb - ta;
        });

        return result;
    }

    function render() {
        const result = filteredAndSorted();
        body.innerHTML = "";

        if (result.length === 0) {
            const row = document.createElement("tr");
            row.innerHTML = '<td colspan="4">Noch keine Historie-Einträge vorhanden.</td>';
            body.appendChild(row);
            status.textContent = "0 Einträge.";
            exportBtn.disabled = true;
            exportBtn.setAttribute("aria-disabled", "true");
            return;
        }

        result.forEach((e) => {
            const row = document.createElement("tr");

            const tdTime = document.createElement("td");
            tdTime.textContent = formatDate(e.created_at);

            const tdType = document.createElement("td");
            tdType.textContent = typeLabel(e.entry_type);

            const tdAction = document.createElement("td");
            tdAction.textContent = actionLabel(e.action);

            const tdDetails = document.createElement("td");
            tdDetails.textContent = String(e.details ?? "");

            row.appendChild(tdTime);
            row.appendChild(tdType);
            row.appendChild(tdAction);
            row.appendChild(tdDetails);
            body.appendChild(row);
        });

        status.textContent = `${result.length} Einträge.`;
        exportBtn.disabled = false;
        exportBtn.setAttribute("aria-disabled", "false");
    }

    async function load() {
        status.textContent = "Lade Historie ...";
        exportBtn.disabled = true;
        exportBtn.setAttribute("aria-disabled", "true");

        try {
            entries = await api("/history");
            if (!Array.isArray(entries)) entries = [];
            render();
        } catch (error) {
            entries = [];
            body.innerHTML = '<tr><td colspan="4">Fehler beim Laden der Historie.</td></tr>';
            status.textContent = `Fehler: ${error.message}`;
        }
    }

    function exportTxt() {
        const result = filteredAndSorted();
        const lines = result.map((e) => {
            const ts = formatDate(e.created_at);
            const type = typeLabel(e.entry_type);
            const action = actionLabel(e.action);
            const details = String(e.details ?? "").replace(/\s+/g, " ").trim();
            return `${ts}\t${type}\t${action}\t${details}`;
        });
        const header = "Zeitpunkt\tTyp\tAktion\tDetails";
        const content = [header, ...lines].join("\n") + "\n";
        const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;
        a.download = "historie.txt";
        document.body.appendChild(a);
        a.click();
        a.remove();

        setTimeout(() => URL.revokeObjectURL(url), 0);
    }

    typeSelect.addEventListener("change", render);
    sortSelect.addEventListener("change", render);
    searchInput.addEventListener("input", render);
    exportBtn.addEventListener("click", () => {
        try {
            exportTxt();
        } catch (error) {
            status.textContent = `Export fehlgeschlagen: ${error.message}`;
        }
    });

    load();
}

function initReportsPage() {
    const previewTitle = document.getElementById("reportsPreviewTitle");
    const previewStatus = document.getElementById("reportsPreviewStatus");
    const previewCanvas = document.getElementById("reportPreviewCanvas");

    if (!previewTitle || !previewStatus || !previewCanvas) return;
    if (typeof window.pdfjsLib === "undefined") {
        previewStatus.textContent = "PDF Vorschau-Bibliothek konnte nicht geladen werden.";
        return;
    }

    const pdfjsLib = window.pdfjsLib;
    pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js";

    async function renderPreview(reportKey) {
        previewTitle.textContent = `Preview: Report ${String(reportKey).toUpperCase()}`;
        previewStatus.textContent = "Lade PDF Vorschau ...";

        try {
            const response = await fetch(`/reports/${reportKey}/preview`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const bytes = await response.arrayBuffer();
            const loadingTask = pdfjsLib.getDocument({ data: bytes });
            const pdf = await loadingTask.promise;
            const page = await pdf.getPage(1);

            const maxWidth = 900;
            const initialViewport = page.getViewport({ scale: 1 });
            const scale = Math.min(1.5, maxWidth / initialViewport.width);
            const viewport = page.getViewport({ scale });

            const ctx = previewCanvas.getContext("2d");
            previewCanvas.width = Math.ceil(viewport.width);
            previewCanvas.height = Math.ceil(viewport.height);

            await page.render({ canvasContext: ctx, viewport }).promise;
            previewStatus.textContent = `Seite 1 von ${pdf.numPages} gerendert.`;
        } catch (error) {
            previewStatus.textContent = `Vorschau fehlgeschlagen: ${error.message}`;
        }
    }

    document.querySelectorAll("button[data-report-preview]").forEach((button) => {
        button.addEventListener("click", () => {
            const reportKey = button.dataset.reportPreview;
            if (!reportKey) return;
            renderPreview(reportKey);
        });
    });

    document.querySelectorAll("button[data-report-download]").forEach((button) => {
        button.addEventListener("click", () => {
            const reportKey = button.dataset.reportDownload;
            if (!reportKey) return;
            window.location.href = `/reports/${reportKey}/download`;
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    if (document.body.classList.contains("page-index")) initIndexPage();
    if (document.body.classList.contains("page-product")) initProductPage();
    if (document.body.classList.contains("page-warehouse") && !document.body.classList.contains("page-history") && !document.body.classList.contains("page-warehouse-detail")) initWarehousePage();
    if (document.body.classList.contains("page-warehouse-detail")) initWarehouseDetailPage();
    if (document.body.classList.contains("page-stats")) initStatsPage();
    if (document.body.classList.contains("page-history")) initHistoryPage();
    if (document.body.classList.contains("page-reports")) initReportsPage();
});
