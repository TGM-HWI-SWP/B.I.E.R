# Application Architecture - B.I.E.R Inventory Management System

## Overview

The B.I.E.R application follows a well-structured, layered architecture pattern to ensure separation of concerns, maintainability, and testability. The architecture comprises four main layers:

1. **Presentation Layer** (Flask Routes)
2. **Business Logic Layer** (Services)
3. **Data Access Layer** (Database Service)
4. **Database Layer** (PostgreSQL Repository)

## Architecture Diagram

```
┌────────────────────────────────────────┐
│      Flask Routes (app.py)             │
│  ── GET /products                      │
│  ── POST /products                     │
│  ── GET /warehouses                    │
│  ── POST /inventory                    │
└────────┬─────────────────────────────┘
         │
┌────────▼────────────────────────────────┐
│    Business Logic Services             │
│  ┌──────────────────────────────────┐  │
│  │ ProductService                   │  │
│  │ - create_product()               │  │
│  │ - get_product()                  │  │
│  │ - list_products()                │  │
│  │ - update_product()               │  │
│  │ - delete_product()               │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │ WarehouseService                 │  │
│  │ - create_warehouse()             │  │
│  │ - list_warehouses()              │  │
│  │ - add_product_to_warehouse()     │  │
│  │ - delete_warehouse()             │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │ InventoryService                 │  │
│  │ - add_product()                  │  │
│  │ - update_quantity()              │  │
│  │ - remove_product()               │  │
│  │ - list_inventory()               │  │
│  └──────────────────────────────────┘  │
└────────┬──────────────────────────────┘
         │
┌────────▼────────────────────────────────┐
│   Database Service (dbService)         │
│  - insert()                            │
│  - find_by_id()                        │
│  - find_all()                          │
│  - update()                            │
│  - delete()                            │
└────────┬──────────────────────────────┘
         │
┌────────▼────────────────────────────────┐
│ PostgreSQL Repository                  │
│  (Direct Database Operations)          │
│  - Connection Management               │
│  - SQL Execution                       │
│  - Transaction Handling                │
└────────────────────────────────────────┘
```

## Layer Descriptions

### 1. Presentation Layer (`app.py`)

**Location:** `src/bierapp/backend/app.py`

**Responsibility:** Handles HTTP requests and responses, routes requests to appropriate services.

**Key Components:**
- Flask application initialization
- Route definitions for all API endpoints
- HTTP request/response handling
- Error handling and status codes
- Input validation

**Entry Point:**
```python
app, db_service, product_service, warehouse_service, inventory_service = create_app()
```

**Benefits:**
- Separation of HTTP concerns from business logic
- Easy to test with Flask test client
- Consistent response format for all endpoints
- Centralized error handling

### 2. Business Logic Layer (Services)

**Location:** `src/bierapp/backend/service/`

**Responsibility:** Implements core business rules and logic.

**Services:**

#### ProductService
- Manages product creation, retrieval, and deletion
- Validates product data (e.g., weight must be positive)
- Enforces business rules for products

#### WarehouseService
- Manages warehouse creation and retrieval
- Handles product-to-warehouse assignments
- Tracks warehouse capacity

#### InventoryService
- Manages inventory quantities
- Tracks products in warehouses
- Validates inventory operations

**Design Pattern:** Each service implements a corresponding Port/Interface from `contracts.py` for dependency injection and testability.

**Benefits:**
- Business logic is independent of database implementation
- Easy to unit test by mocking the database layer
- Reusable across different presentation layers (API, CLI, etc.)

### 3. Data Access Layer (`dbService`)

**Location:** `src/bierapp/backend/service/db_Service.py`

**Responsibility:** Wraps the database repository and provides a unified database interface.

**Key Methods:**
- `connect()` - Establish database connection
- `insert()` - Create new records
- `find_by_id()` - Retrieve single record
- `find_all()` - Retrieve all records
- `update()` - Modify existing records
- `delete()` - Remove records

**Design Pattern:** Adapter pattern - implements DatabasePort interface.

**Benefits:**
- Allows swapping database implementations without affecting services
- Centralized connection management
- Consistent error handling

### 4. Database Layer (`PostgresRepository`)

**Location:** `src/bierapp/db/postgress.py`

**Responsibility:** Low-level database operations with PostgreSQL.

**Capabilities:**
- Connection pooling and management
- Direct SQL execution
- Result mapping to Python dictionaries
- Transaction management

**Benefits:**
- Encapsulates vendor-specific database details
- Reusable database adapter pattern
- Easy to mock for testing

## Data Flow Example: Create Product

```
1. HTTP Request
   POST /products
   Body: {"name": "Product A", "gewicht": 2.5}

2. Flask Route Handler
   ├─ Validates request JSON structure
   ├─ Extracts and validates required fields
   └─ Calls ProductService.create_product()

3. ProductService
   ├─ Validates business rules (weight > 0)
   ├─ Prepares data dictionary
   └─ Calls dbService.insert("products", data)

4. dbService
   ├─ Unwraps repository
   └─ Calls PostgresRepository.insert()

5. PostgresRepository
   ├─ Builds SQL INSERT statement
   ├─ Executes with parameterized query
   ├─ Commits transaction
   └─ Returns inserted record ID

6. Response Chain (Reversed)
   ├─ ProductService returns product with ID
   ├─ Flask handler returns JSON with 201 status
   └─ HTTP Response sent to client
```

## Configuration

### Application Setup

All configuration is handled through the `Config` class in `app.py`:

```python
class Config:
    RESOURCES_DIR = ...  # Static files
    TEMPLATES_DIR = ...  # HTML templates
    STYLESHEETS_DIR = ... # CSS stylesheets
```

### Database Configuration

Environment variables (with defaults):
- `POSTGRES_HOST` - Database host (default: localhost)
- `POSTGRES_PORT` - Database port (default: 5432)
- `POSTGRES_DB` - Database name (default: lagerverwaltung)
- `POSTGRES_USER` - Database user (default: admin)
- `POSTGRES_PASSWORD` - Database password (default: secret)

## API Endpoints

### Product APIs
- `GET /products` - List all products
- `POST /products` - Create new product
- `GET /products/<id>` - Get specific product
- `PUT /products/<id>` - Update product
- `DELETE /products/<id>` - Delete product

### Warehouse APIs
- `GET /warehouses` - List all warehouses
- `POST /warehouses` - Create new warehouse
- `DELETE /warehouses/<id>` - Delete warehouse

### Inventory APIs
- `POST /inventory` - Add product to warehouse
- `GET /inventory/<warehouse_id>/products` - Get warehouse inventory
- `POST /lagerprodukte` - Alternative endpoint for inventory management

## Error Handling

The application implements comprehensive error handling:

1. **Input Validation** - Request body validation in routes
2. **Business Logic Validation** - Value validation in services
3. **HTTP Error Handlers** - Global handlers for 400, 404, 500 errors
4. **Exception Propagation** - Clear error messages in responses

## Running the Application

### From Root Directory
```bash
python run.py
```

### From Backend Directory
```bash
python -m bierapp.backend.app
```

### With Custom Configuration
```bash
POSTGRES_HOST=myhost POSTGRES_USER=myuser python run.py
```

## Development Best Practices

1. **Add business rules in Services** - Not in routes or database layer
2. **Use dependency injection** - Pass services to routes via `create_app()`
3. **Follow naming conventions** - English method names, clear variable names
4. **Add docstrings** - Follow the existing Google-style format
5. **Validate early** - Validate in routes and services
6. **Use type hints** - All method signatures include type hints
7. **Commit data consistently** - All database writes commit immediately
8. **Test layers independently** - Mock dependencies for unit tests

## Future Improvements

1. Add caching layer (Redis)
2. Implement pagination for list endpoints
3. Add transaction batching for bulk operations
4. Implement audit logging
5. Add request rate limiting
6. Implement database connection pooling
7. Add async/await support for I/O operations
