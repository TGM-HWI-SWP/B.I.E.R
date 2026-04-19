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
    const unitInput = document.getElementById("productUnit");
    const status = document.getElementById("page1Status");

    const saveBtn = document.getElementById("saveProductBtn");
    const discardBtn = document.getElementById("discardProductBtn");
    const resetBtn = document.getElementById("resetProductBtn");
    const deleteBtn = document.getElementById("deleteAttributeBtn");
    const addAttrBtn = document.getElementById("addAttributeBtn");

    if (!productSelect || !warehouseStocks || !nameInput || !descriptionInput || !weightInput || !unitInput || !status || !saveBtn || !discardBtn || !resetBtn || !deleteBtn || !addAttrBtn) return;

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
        unitInput.value = "Stk";
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
        descriptionInput.value = product.beschreibung || "";
        weightInput.value = product.gewicht ?? "";
        unitInput.value = product.einheit || "Stk";
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
    const searchInput = document.getElementById("warehouseSearch");
    const nameInput = document.getElementById("warehouseName");
    const addressInput = document.getElementById("warehouseAddress");
    const capacityInput = document.getElementById("warehouseCapacity");
    const companyInput = document.getElementById("warehouseCompany");

    if (!body || !status || !createBtn || !searchInput || !nameInput || !addressInput || !capacityInput || !companyInput) return;

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
            row.innerHTML = '<td colspan="6">Keine Lager zur Suche gefunden.</td>';
            body.appendChild(row);
            return;
        }

        visibleWarehouses.forEach((warehouse) => {
            const products = Number(warehouse.products || 0);
            const capacity = Number(warehouse.max_plaetze || 0);
            const utilization = capacity > 0 ? Math.round((products / capacity) * 100) : 0;
            const row = document.createElement("tr");
            row.dataset.id = String(warehouse.id);
            row.className = "warehouse-row-clickable";
            row.tabIndex = 0;
            row.setAttribute("aria-label", `Lager ${warehouse.lagername ?? warehouse.id} öffnen`);
            row.innerHTML = `
                <td>${warehouse.lagername ?? ""}</td>
                <td>${warehouse.adresse ?? ""}</td>
                <td><span class="pill">${products} Produkte</span></td>
                <td><span class="pill">${capacity} max.</span></td>
                <td><span class="pill">${utilization}%</span></td>
                <td class="actions">
                    <button class="btn btn-small" type="button" data-open-id="${warehouse.id}">Öffnen</button>
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

        const row = target instanceof Element ? target.closest("tr[data-id]") : null;
        if (!row) return;
        const id = row.dataset.id;
        if (!id) return;
        openWarehouseDetail(id);
    });

    body.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        const target = event.target;
        if (!(target instanceof Element)) return;
        const row = target.closest("tr[data-id]");
        if (!row || !row.dataset.id) return;
        openWarehouseDetail(row.dataset.id);
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

    if (!body || !status || !title || !subtitle || !backLink) return;

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
    let warehouses = [];
    let inventoryRows = [];

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
        productsById = new Map(productsData.map((p) => [String(p.id), p.name || `Produkt ${p.id}`]));
        inventoryRows = inventoryData;

        const currentWarehouse = warehouses.find((w) => String(w.id) === String(warehouseId));
        const warehouseName = currentWarehouse?.lagername || `Lager ${warehouseId}`;
        title.textContent = `${warehouseName} (ID ${warehouseId})`;
        subtitle.textContent = currentWarehouse
            ? `${currentWarehouse.adresse || "Ohne Adresse"} - Produkte im Lager verwalten`
            : "Produkte im Lager verwalten";

        renderTable();
        status.textContent = `${inventoryRows.length} Produktposition(en) geladen.`;
    }

    async function getInventoryQuantity(lagerId, productId) {
        const rows = await api(`/inventory/${lagerId}/products`);
        const item = rows.find((r) => String(r.produkt_id) === String(productId));
        return item ? Number(item.menge || 0) : 0;
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

                const sourceQty = await getInventoryQuantity(warehouseId, productId);
                if (moveQty > sourceQty) {
                    throw new Error("Verschiebemenge ist größer als der Bestand im Quelllager.");
                }

                const targetQty = await getInventoryQuantity(targetWarehouseId, productId);
                await Promise.all([
                    api("/inventory", {
                        method: "PUT",
                        body: JSON.stringify({
                            lager_id: Number(warehouseId),
                            produkt_id: Number(productId),
                            menge: sourceQty - moveQty,
                        }),
                    }),
                    api("/inventory", {
                        method: "PUT",
                        body: JSON.stringify({
                            lager_id: Number(targetWarehouseId),
                            produkt_id: Number(productId),
                            menge: targetQty + moveQty,
                        }),
                    }),
                ]);

                await refresh();
                status.textContent = `Produkt ${productId} nach Lager ${targetWarehouseId} verschoben.`;
            }
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
