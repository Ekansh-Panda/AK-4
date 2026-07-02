# @miori/types

Shared TypeScript contracts for Miori Core. These interfaces mirror the
FastAPI response/request schemas in `services/core-api/app/schemas/` and are
imported by both `apps/desktop` and `apps/remote-dashboard`.

```ts
import type { ChatMessage, DeviceStatus, PersonaMode } from "@miori/types";
```

No runtime code — types only, zero bundle cost.

> When you change a backend schema, update the matching interface here so the
> frontends stay in sync. A future task (see `TASKS.md`) is to auto-generate
> these from the OpenAPI spec.
