const API_BASE = "http://localhost:5000";

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
            container.innerHTML = "<div>Keine Produkte vorhanden.</div>";
            return;
        }

        products.forEach(p => {
            const el = document.createElement("div");
            el.className = "results-placeholder";
            el.textContent = p.name || ("Produkt " + p.produkt_id);
            container.appendChild(el);
        });

    } catch {
        container.innerHTML = "<div>Fehler beim Laden</div>";
    }
}

/* =========================
   CREATE PRODUCT (2-STEP!)
========================= */

async function createProduct() {

    const supplier = document.getElementById("productSupplier").value.trim();
    const price = Number(document.getElementById("productPrice").value);
    const warehouse = Number(document.getElementById("productWarehouse").value);
    const amount = Number(document.getElementById("productAmount").value);

    if (!supplier || isNaN(price) || isNaN(amount) || isNaN(warehouse)) {
        alert("Bitte gültige Daten eingeben");
        return;
    }

    try {
        // 1️⃣ Produkt erstellen
        const product = await api("/products", {
            method: "POST",
            body: JSON.stringify({
                name: supplier,
                gewicht: price,
                beschreibung: ""
            })
        });

        // 2️⃣ Produkt dem Lager zuweisen
        await api("/inventory", {
            method: "POST",
            body: JSON.stringify({
                lager_id: warehouse,
                produkt_id: product.id,
                menge: amount
            })
        });

        alert("Produkt gespeichert");

        // Reset
        document.getElementById("productSupplier").value = "";
        document.getElementById("productPrice").value = "";
        document.getElementById("productAmount").value = "";

        loadProducts();
        loadWarehouses();

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
                <td>${w.products || 0}</td>
                <td>${w.max_plaetze}</td>
                <td>${usage}%</td>
                <td>
                    <button class="deleteWarehouse">Löschen</button>
                </td>
            `;

            row.querySelector(".deleteWarehouse").onclick = async () => {
                if (!confirm("Wirklich löschen?")) return;

                try {
                    await api(`/warehouses/${w.id}`, {
                        method: "DELETE"
                    });

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

    const name = document.getElementById("warehouseName").value.trim();
    const adresse = document.getElementById("warehouseLocation").value;
    const capacity = Number(document.getElementById("warehouseCapacity").value);

    if (!name || isNaN(capacity)) {
        alert("Bitte gültige Daten eingeben");
        return;
    }

    try {
        await api("/warehouses", {
            method: "POST",
            body: JSON.stringify({
                lagername: name,
                adresse: adresse,
                max_plaetze: capacity,
                firma_id: 1   // 🔥 wichtig (fix oder später auswählbar machen)
            })
        });

        // Reset
        document.getElementById("warehouseName").value = "";
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

    document.getElementById("saveProductBtn")
        ?.addEventListener("click", createProduct);

    document.getElementById("createWarehouseBtn")
        ?.addEventListener("click", createWarehouse);
});