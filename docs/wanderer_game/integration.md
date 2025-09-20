# Discord Cog & Service Integration Guide


## Overview

This document explains how the Discord bot cog (`ExpeditionsCog`) integrates with the backend service layer (`DatabaseService`) in the expedition game system. It covers the command flow, service container usage, extension points, and troubleshooting tips for developers.

---

## Architecture & Flow

### Key Components

- **ExpeditionsCog** (`cogs/commands/expeditions.py`): Handles Discord slash commands and UI for expeditions. Implements user interactions, embeds, and views.
- **ServiceContainer**: Dependency injection container that provides access to backend services (e.g., `expedition_service`, `database_service`).
- **ExpeditionService**: Orchestrates expedition logic, interacts with the database, and exposes high-level methods for the cog.
- **DatabaseService** (`services/database.py`): Handles all database operations, including expedition records, user data, and inventory management.

### Command Flow Example

1. **User triggers a Discord command** (e.g., `/nwnl_expeditions_start`).
2. **ExpeditionsCog** receives the command and defers the response for async processing.
3. The cog uses the **service container** to access `expedition_service` and, through it, the `database_service`.
4. The cog fetches user data, available expeditions, and character info via service methods.
5. The cog builds Discord UI (views, embeds, modals) and sends them to the user.
6. User interactions (button clicks, selects) are handled by the cog, which may trigger further service/database calls.
7. Expedition actions (start, complete, claim rewards) are processed by the backend, and results are returned to the user via Discord UI.

#### Sequence Diagram (Textual)

```text
User -> Discord UI -> ExpeditionsCog -> ExpeditionService -> DatabaseService -> DB
   <- UI/Embed/Response <-           <-                <-
```

---

## Extension Points

- **Add New Commands**: Extend `ExpeditionsCog` with new `@app_commands.command` methods.
- **Custom UI**: Create new `discord.ui.View` subclasses for advanced interactions.
- **Backend Logic**: Add methods to `ExpeditionService` or `DatabaseService` for new features.
- **Service Injection**: Register new services in `ServiceContainer` for modularity.

---

## Troubleshooting Integration

- **No Response in Discord**: Check for exceptions in the cog or service logs. Ensure async methods are awaited.
- **Database Errors**: Verify the database connection pool is initialized (`await DatabaseService.initialize()`).
- **Data Not Updating**: Ensure service methods are called and results are handled in the cog.
- **UI Not Updating**: Confirm that `interaction.response.edit_message` or `followup.send` is used correctly.
- **Debugging**: Use logging in both cog and service layers. The cog logs user actions and errors; the service logs database and logic errors.

---

## Best Practices

- Keep UI logic in the cog, business logic in the service, and data access in the database service.
- Use the service container for dependency injection to keep code modular and testable.
- Handle all exceptions gracefully and provide user feedback in Discord.

---

For more details, see the code in `cogs/commands/expeditions.py` and `services/database.py`, and the rest of the documentation in this folder.
