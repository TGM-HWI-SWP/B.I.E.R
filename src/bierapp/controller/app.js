const API_BASE = "http://localhost:3000";

async function api(endpoint, options = {}) {
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            },
            ...options
        });

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        if (res.status === 204) return null;

        return await res.json();

    } catch (err) {
        console.error("API Error:", err);
        alert("Fehler bei der Serverkommunikation");
        throw err;
    }
}

/* =========================
   PRODUCTS
========================= */

async function loadProducts() {
    const container = document.getElementById("productList");
    if (!container) return;

    container.innerHTML = "Lade Produkte...";

    try {
        const products = await api("/products");

        container.innerHTML = "";

        if (!products || products.length === 0) {
            container.innerHTML = "<div class='results-note'>Keine Produkte vorhanden.</div>";
            return;
        }

        products.forEach(p => {
            const el = document.createElement("div");
            el.className = "results-placeholder";
            el.textContent = p.name || `Produkt ${p.id}`;
            container.appendChild(el);
        });

    } catch {
        container.innerHTML = "<div class='error'>Fehler beim Laden der Produkte</div>";
    }
}

/* =========================
   CREATE PRODUCT
========================= */

async function createProduct() {
    const supplier = document.getElementById("productSupplier");
    if (!supplier) return;

    const data = {
        supplier: supplier.value.trim(),
        price: Number(document.getElementById("productPrice").value),
        currency: document.getElementById("productCurrency").value,
        warehouse: document.getElementById("productWarehouse").value,
        amount: Number(document.getElementById("productAmount").value)
    };

    if (!data.supplier || isNaN(data.price) || isNaN(data.amount)) {
        alert("Bitte gültige Daten eingeben");
        return;
    }

    try {
        await api("/products", {
            method: "POST",
            body: JSON.stringify(data)
        });

        alert("Produkt gespeichert");

        supplier.value = "";
        document.getElementById("productPrice").value = "";
        document.getElementById("productAmount").value = "";

        loadProducts();

    } catch {}
}

/* =========================
   WAREHOUSES
========================= */

async function loadWarehouses() {
    const table = document.getElementById("warehouseTable");
    if (!table) return;

    table.innerHTML = "<tr><td colspan='6'>Lade Lager...</td></tr>";

    try {
        const warehouses = await api("/warehouses");

        table.innerHTML = "";

        warehouses.forEach(w => {
            const usage = w.max_plaetze
                ? Math.round((w.products || 0) / w.max_plaetze * 100)
                : 0;

            const row = document.createElement("tr");

            row.innerHTML = `
                <td>${w.lagername}</td>
                <td>${w.adresse}</td>
                <td><span class="pill">${w.products || 0} Produkte</span></td>
                <td><span class="pill">${w.max_plaetze}</span></td>
                <td><span class="pill">${usage}%</span></td>
                <td>
                    <button class="btn btn-small deleteWarehouse">Löschen</button>
                </td>
            `;

            row.querySelector(".deleteWarehouse").onclick = async () => {
                if (!confirm("Wirklich löschen?")) return;

                try {
                    await api(`/warehouses/${w.id}`, { method: "DELETE" });
                    row.remove();
                } catch {}
            };

            table.appendChild(row);
        });

    } catch {
        table.innerHTML = "<tr><td colspan='6'>Fehler beim Laden</td></tr>";
    }
}

/* =========================
   CREATE WAREHOUSE
========================= */

async function createWarehouse() {
    const name = document.getElementById("warehouseName");
    if (!name) return;

    const data = {
        lagername: name.value.trim(),
        adresse: document.getElementById("warehouseLocation").value,
        max_plaetze: Number(document.getElementById("warehouseCapacity").value)
    };

    if (!data.lagername || isNaN(data.max_plaetze)) {
        alert("Bitte gültige Daten eingeben");
        return;
    }

    try {
        await api("/warehouses", {
            method: "POST",
            body: JSON.stringify(data)
        });

        name.value = "";
        document.getElementById("warehouseLocation").value = "";
        document.getElementById("warehouseCapacity").value = "";

        loadWarehouses();

    } catch {}
}

/* =========================
   INIT
========================= */

document.addEventListener("DOMContentLoaded", () => {
    loadProducts();
    loadWarehouses();

    document.getElementById("saveProductBtn")?.addEventListener("click", createProduct);
    document.getElementById("createWarehouseBtn")?.addEventListener("click", createWarehouse);
});