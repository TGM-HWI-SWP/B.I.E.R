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
    const warehouseSelect = document.getElementById("warehouseSelect");
    const nameInput = document.getElementById("productName");
    const descriptionInput = document.getElementById("productDescription");
    const weightInput = document.getElementById("productWeight");
    const quantityInput = document.getElementById("warehouseQuantity");
    const status = document.getElementById("page1Status");
    const createBtn = document.getElementById("createProductBtn");
    const updateBtn = document.getElementById("updateProductBtn");
    const assignBtn = document.getElementById("assignWarehouseBtn");
    const deleteBtn = document.getElementById("deleteProductBtn");

    if (!productSelect || !warehouseSelect || !nameInput || !descriptionInput || !weightInput || !quantityInput || !status || !createBtn || !updateBtn || !assignBtn || !deleteBtn) return;

    let products = [];

    function fillProductForm(productId) {
        const product = products.find((item) => String(item.id) === String(productId));
        if (!product) {
            nameInput.value = "";
            descriptionInput.value = "";
            weightInput.value = "";
            return;
        }
        nameInput.value = product.name || "";
        descriptionInput.value = product.beschreibung || "";
        weightInput.value = product.gewicht || "";
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
        fillProductForm(productSelect.value);
    }

    async function loadProducts() {
        products = await api("/products");
        renderProductOptions();
    }

    async function loadWarehouses() {
        const warehouses = await api("/warehouses");
        warehouseSelect.innerHTML = '<option value="">Lager wählen</option>';
        warehouses.forEach((warehouse) => {
            const option = document.createElement("option");
            option.value = String(warehouse.id);
            option.textContent = `${warehouse.id} - ${warehouse.lagername}`;
            warehouseSelect.appendChild(option);
        });
    }

    function productPayload() {
        return {
            name: nameInput.value.trim(),
            beschreibung: descriptionInput.value.trim(),
            gewicht: Number(weightInput.value),
        };
    }

    async function createProduct() {
        const payload = productPayload();
        if (!payload.name || !payload.gewicht) {
            throw new Error("Name und Gewicht sind Pflichtfelder.");
        }
        const created = await api("/products", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        await loadProducts();
        productSelect.value = String(created.id);
        fillProductForm(created.id);
        status.textContent = `Produkt ${created.id} erstellt.`;
    }

    async function updateProduct() {
        const productId = productSelect.value;
        if (!productId) throw new Error("Bitte zuerst ein bestehendes Produkt auswählen.");
        const payload = productPayload();
        await api(`/products/${productId}`, {
            method: "PUT",
            body: JSON.stringify(payload),
        });
        await loadProducts();
        productSelect.value = String(productId);
        fillProductForm(productId);
        status.textContent = `Produkt ${productId} aktualisiert.`;
    }

    async function deleteProduct() {
        const productId = productSelect.value;
        if (!productId) throw new Error("Bitte zuerst ein Produkt auswählen.");
        if (!confirm(`Produkt ${productId} löschen?`)) return;
        await api(`/products/${productId}`, { method: "DELETE" });
        await loadProducts();
        status.textContent = `Produkt ${productId} gelöscht.`;
    }

    async function assignToWarehouse() {
        const productId = productSelect.value;
        const warehouseId = warehouseSelect.value;
        const qty = Number(quantityInput.value);
        if (!productId) throw new Error("Bitte zuerst ein Produkt auswählen.");
        if (!warehouseId) throw new Error("Bitte ein Lager auswählen.");
        if (!qty || qty < 1) throw new Error("Menge muss mindestens 1 sein.");

        await api("/lagerprodukte", {
            method: "POST",
            body: JSON.stringify({ lager_id: Number(warehouseId), produkt_id: Number(productId), menge: qty }),
        });
        status.textContent = `Produkt ${productId} mit Menge ${qty} in Lager ${warehouseId} gebucht.`;
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

    productSelect.addEventListener("change", () => fillProductForm(productSelect.value));
    bind(createBtn, createProduct);
    bind(updateBtn, updateProduct);
    bind(assignBtn, assignToWarehouse);
    bind(deleteBtn, deleteProduct);

    (async function init() {
        try {
            status.textContent = "Lade Produkt- und Lagerdaten ...";
            await Promise.all([loadProducts(), loadWarehouses()]);
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

document.addEventListener("DOMContentLoaded", () => {
    if (document.body.classList.contains("page-index")) initIndexPage();
    if (document.body.classList.contains("page-product")) initProductPage();
    if (document.body.classList.contains("page-warehouse")) initWarehousePage();
    if (document.body.classList.contains("page-stats")) initStatsPage();
});
