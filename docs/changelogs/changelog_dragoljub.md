# Project Changelog (Dragoljub)

This changelog lists each project version update and the related commits to document the project progress.

---

## 06.03.2026 - Docker Configuration Update

Updated the Docker configuration.

Commits:
- 26e09fc - Update docker.yml

---

## 13.03.2026 - Service and Database Connection

Created the service layer, implemented the base structure for the database connection, and connected `postgress.py` with `service.py`.

Commits:
- 431e80a - create service.py
- 67357f5 - Implenting base structure for DB-Connection
- 9d46192 - Implementing connection between postgress.py and service.py

---

## 20.03.2026 - API Integration and Layer Preparation

Added an API caller, synchronized database connections, updated the GUI, and prepared the groundwork for layer-based architecture.

Commits:
- 5edea58 - api caller added
- 09318c6 - gui.py updated
- 4f494a6 - Basic Api caller and DB Connection Syncing
- 2556363 - extending ground for Layer connections

---

## 27.03.2026 - Service Refactoring

Refactored the service layer by splitting `service.py` into multiple modules and updated the GUI accordingly.

Commits:
- f560535 - Splitting service.py in three seperate service modules
- 22a2d56 - Update gui.py for service Splitting

## 17.04.2026 - Service Architecture and Code Quality Improvements

Refactored backend services to improve architecture, enforce coding standards, and reduce code duplication.

Changes:
- Renamed `dbService` to `DbService` for PEP 8 compliance and updated all imports and references
- Extracted `_find_inventory_item()` helper method to eliminate duplicated inventory search logic
- Refactored `update_quantity()` and `remove_product()` to use the new helper method
- Implemented `WarehouseServicePort` in `WarehouseService`
- Fixed `create_warehouse()` method signature by adding `firma_id` parameter
- Implemented missing `update_warehouse()` method in `WarehouseService`
- Updated `WarehouseServicePort` contract to include `firma_id: int`
- Refactored `WarehouseService` to use dependency injection for `InventoryService`
- Removed duplicate instantiation of `InventoryService`
- Updated `app.py` to properly inject `InventoryService` into `WarehouseService`
- Fixed circular import issues by importing from contracts instead of services
- Updated module exports in `__init__.py` to use `DbService`
- Updated imports in `warehouse_service.py` to use contracts

Impact:
- Improved adherence to the Single Responsibility Principle
- Eliminated redundant code (DRY principle)
- Ensured full contract compliance of all services
- Increased type safety and consistency in dependencies
- Achieved PEP 8 compliant naming conventions

Files Modified:
- db_Service.py
- product_service.py
- warehouse_service.py
- app.py
- contracts.py

Commits:
- <commit-hash> - Refactor: Service architecture and code quality improvements