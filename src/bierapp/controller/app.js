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
            const id = String(product.id || "").toLowerCase();
            return name.includes(query) || description.includes(query) || id.includes(query);
        });

        body.innerHTML = "";
        if (filtered.length === 0) {
            const row = document.createElement("tr");
            row.innerHTML = '<td colspan="5">Keine Produkte gefunden.</td>';
            body.appendChild(row);
            return;
        }

        filtered.forEach((product) => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${product.id ?? ""}</td>
                <td>${product.name ?? ""}</td>
                <td>${product.beschreibung ?? ""}</td>
                <td>${product.gewicht ?? ""}</td>
                <td><button class="btn btn-small" type="button" data-id="${product.id}">Löschen</button></td>
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
    const descriptionInput = document.getElementById("productDescription");
    const weightInput = document.getElementById("productWeight");
    const status = document.getElementById("page1Status");

    const saveBtn = document.getElementById("saveProductBtn");
    const discardBtn = document.getElementById("discardProductBtn");
    const resetBtn = document.getElementById("resetProductBtn");
    const deleteBtn = document.getElementById("deleteAttributeBtn");
    const addAttrBtn = document.getElementById("addAttributeBtn");

    if (!productSelect || !warehouseStocks || !nameInput || !descriptionInput || !weightInput || !status || !saveBtn || !discardBtn || !resetBtn || !deleteBtn || !addAttrBtn) return;

    const title = document.querySelector(".product-title");
    const subtitle = document.querySelector(".product-subtitle");

    let products = [];
    let warehouses = [];
    let loadedInventory = new Map();

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
        descriptionInput.value = "";
        weightInput.value = "";
        for (const input of warehouseStocks.querySelectorAll("input[data-warehouse-id]")) {
            input.value = "0";
        }
        loadedInventory = new Map();
        setHeader("");
    }

    function productPayload() {
        return {
            name: nameInput.value.trim(),
            beschreibung: descriptionInput.value.trim(),
            gewicht: Number(weightInput.value),
        };
    }

    function fillProductForm(productId) {
        const product = products.find((item) => String(item.id) === String(productId));
        if (!product) {
            clearForm();
            return;
        }
        nameInput.value = product.name || "";
        descriptionInput.value = product.beschreibung || "";
        weightInput.value = product.gewicht ?? "";
        setHeader(productId);
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
        if (!payload.name || !payload.gewicht) {
            throw new Error("Name und Gewicht sind Pflichtfelder.");
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
            status.textContent = `Produkt ${created.id} erstellt.`;
            return String(created.id);
        }

        await api(`/products/${existingId}`, {
            method: "PUT",
            body: JSON.stringify(payload),
        });
        await loadProducts();
        productSelect.value = String(existingId);
        fillProductForm(existingId);
        status.textContent = `Produkt ${existingId} aktualisiert.`;
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
        status.textContent = `Produkt ${productId} gespeichert.`;
    }

    async function deleteProduct() {
        const productId = productSelect.value;
        if (!productId) throw new Error("Bitte zuerst ein Produkt auswählen.");
        if (!confirm(`Produkt ${productId} löschen?`)) return;
        await api(`/products/${productId}`, { method: "DELETE" });
        await loadProducts();
        productSelect.value = "";
        clearForm();
        status.textContent = `Produkt ${productId} gelöscht.`;
    }

    async function discardChanges() {
        const productId = productSelect.value;
        fillProductForm(productId);
        await loadInventoryForProduct(productId);
        status.textContent = productId ? "Änderungen verworfen." : "Zurückgesetzt.";
    }

    function bind(button, action) {
        button.addEventListener("click", async () => {
            try {
                await action();
            } catch (error) {
                status.textContent = `Fehler: ${error.message}`;
            }
        });
    }

    productSelect.addEventListener("change", async () => {
        const productId = productSelect.value;
        fillProductForm(productId);
        try {
            await loadInventoryForProduct(productId);
        } catch (error) {
            status.textContent = `Fehler beim Laden des Bestands: ${error.message}`;
        }
    });

    bind(saveBtn, saveAll);
    bind(discardBtn, discardChanges);
    bind(resetBtn, discardChanges);
    bind(deleteBtn, deleteProduct);
    addAttrBtn.addEventListener("click", () => {
        status.textContent = "Attribut-Management ist noch nicht implementiert.";
    });

    (async function init() {
        try {
            status.textContent = "Lade Produkt- und Lagerdaten ...";
            await Promise.all([loadProducts(), loadWarehouses()]);
            fillProductForm(productSelect.value);
            await loadInventoryForProduct(productSelect.value);
            status.textContent = "Bereit.";
        } catch (error) {
            status.textContent = `Initialisierung fehlgeschlagen: ${error.message}`;
        }
    })();
}

function initWarehousePage() {
    const body = document.getElementById("warehousesTableBody");
    const status = document.getElementById("warehousesStatus");
    const createBtn = document.getElementById("createWarehouseBtn");
    const nameInput = document.getElementById("warehouseName");
    const addressInput = document.getElementById("warehouseAddress");
    const capacityInput = document.getElementById("warehouseCapacity");
    const companyInput = document.getElementById("warehouseCompany");

    if (!body || !status || !createBtn || !nameInput || !addressInput || !capacityInput || !companyInput) return;

    function renderRows(warehouses) {
        body.innerHTML = "";
        if (!warehouses.length) {
            const row = document.createElement("tr");
            row.innerHTML = '<td colspan="6">Noch keine Lager vorhanden.</td>';
            body.appendChild(row);
            return;
        }

        warehouses.forEach((warehouse) => {
            const products = Number(warehouse.products || 0);
            const capacity = Number(warehouse.max_plaetze || 0);
            const utilization = capacity > 0 ? Math.round((products / capacity) * 100) : 0;
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${warehouse.lagername ?? ""}</td>
                <td>${warehouse.adresse ?? ""}</td>
                <td><span class="pill">${products} Produkte</span></td>
                <td><span class="pill">${capacity} max.</span></td>
                <td><span class="pill">${utilization}%</span></td>
                <td><button class="btn btn-small" type="button" data-id="${warehouse.id}">Löschen</button></td>
            `;
            body.appendChild(row);
        });
    }

    async function loadWarehouses() {
        status.textContent = "Lade Lager ...";
        const warehouses = await api("/warehouses");
        renderRows(warehouses);
        status.textContent = `${warehouses.length} Lager geladen.`;
    }

    async function createWarehouse() {
        const payload = {
            lagername: nameInput.value.trim(),
            adresse: addressInput.value.trim(),
            max_plaetze: Number(capacityInput.value),
            firma_id: Number(companyInput.value),
        };
        if (!payload.lagername || !payload.adresse || !payload.max_plaetze || !payload.firma_id) {
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

    body.addEventListener("click", async (event) => {
        const target = event.target;
        if (!(target instanceof HTMLButtonElement)) return;
        const id = target.dataset.id;
        if (!id) return;
        if (!confirm(`Lager ${id} wirklich löschen?`)) return;
        try {
            await deleteWarehouse(id);
        } catch (error) {
            status.textContent = `Fehler: ${error.message}`;
        }
    });

    loadWarehouses().catch((error) => {
        status.textContent = `Fehler beim Laden: ${error.message}`;
    });
}

function initStatsPage() {
    const warehousesValue = document.getElementById("kpiWarehouses");
    const productsValue = document.getElementById("kpiProducts");
    const topProductValue = document.getElementById("kpiTopProduct");
    const topProductSub = document.getElementById("kpiTopProductSub");
    const maxUtilValue = document.getElementById("kpiMaxUtil");
    const maxUtilSub = document.getElementById("kpiMaxUtilSub");
    const chartHost = document.getElementById("chartWarehouses");
    const topHost = document.getElementById("topProducts");

    if (!warehousesValue || !productsValue || !topProductValue || !topProductSub || !maxUtilValue || !maxUtilSub || !chartHost || !topHost) return;

    (async function run() {
        try {
            const [warehouses, products] = await Promise.all([api("/warehouses"), api("/products")]);
            const productMap = new Map(products.map((product) => [String(product.id), product.name || `Produkt ${product.id}`]));
            const inventoryByWarehouse = [];
            const productTotals = new Map();

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
                    const current = productTotals.get(productId) || 0;
                    productTotals.set(productId, current + Number(item.menge || 0));
                });
            }

            const topProducts = Array.from(productTotals.entries())
                .map(([id, qty]) => ({ name: productMap.get(id) || `Produkt ${id}`, qty }))
                .sort((a, b) => b.qty - a.qty);

            const totalWarehouses = warehouses.length;
            const totalProducts = inventoryByWarehouse.reduce((sum, item) => sum + item.products, 0);
            const topProduct = topProducts[0] || null;
            const byUtil = inventoryByWarehouse
                .map((item) => ({ ...item, util: item.capacity > 0 ? item.products / item.capacity : 0 }))
                .sort((a, b) => b.util - a.util);
            const maxUtil = byUtil[0] || null;

            warehousesValue.textContent = String(totalWarehouses);
            productsValue.textContent = String(totalProducts);
            topProductValue.textContent = topProduct ? topProduct.name : "-";
            topProductSub.textContent = topProduct ? `${topProduct.qty} Stk.` : "-";

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
        } catch (error) {
            warehousesValue.textContent = "!";
            productsValue.textContent = "!";
            topProductValue.textContent = "Fehler";
            topProductSub.textContent = error.message;
            maxUtilValue.textContent = "!";
            maxUtilSub.textContent = error.message;
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

document.addEventListener("DOMContentLoaded", () => {
    if (document.body.classList.contains("page-index")) initIndexPage();
    if (document.body.classList.contains("page-product")) initProductPage();
    if (document.body.classList.contains("page-warehouse") && !document.body.classList.contains("page-history")) initWarehousePage();
    if (document.body.classList.contains("page-stats")) initStatsPage();
    if (document.body.classList.contains("page-history")) initHistoryPage();
});
