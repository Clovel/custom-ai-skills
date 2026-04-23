---
name: nestjs-paginated-list-routes
description: Use when adding, reviewing, or fixing paginated GET list endpoints in a NestJS + Prisma + nestjs-zod backend. Enforces the PaginationQueryBaseSchema / createPaginatedResponseDto / buildPaginatedResponse + ISO-string-dates + @ApiExtraModels pattern across controller, service, and DTO.
---

# NestJS Paginated List Routes

## Overview

Every paginated `GET` list endpoint follows one shape so typing errors are caught at compile time (not at OpenAPI generation or runtime), and API consumers get consistent named types.

```
Query DTO          ──extends──> PaginationQueryBaseSchema  (+ refineSkipAlignedWithLimit)
Response DTO       ──extends──> createPaginatedResponseDto(itemSchema)
Service return     ==           named FooListResponseDTO class
Service body       ──calls──>   buildPaginatedResponse({ items, total, skip, limit })
Date fields        ──via──>     .toISOString()  (with `?? null` for nullable)
Controller         ──decorates> @ApiExtraModels(FooQueryDTO) + @ApiResponse({ type: FooListResponseDTO })
```

## Prerequisites

- **Zod v4** (uses `z.iso.datetime()` / `z.coerce.number()`; v3 equivalents exist but the examples below assume v4).
- **`nestjs-zod`** for `createZodDto`.
- **Four helpers** in the project (`PaginationQueryBaseSchema`, `refineSkipAlignedWithLimit`, `createPaginatedResponseDto`, `buildPaginatedResponse`). If your project doesn't have them yet, see `references/canonical-helpers.md` for drop-in source.
- **A Prisma client accessible on the service class.** Examples assume `this.prisma` (from an injected `PrismaService`). If your project injects it differently (`@InjectConnection()`, a custom repository, etc.), substitute accordingly. Inside a `prisma.$transaction(async (tx) => ...)` callback, swap `this.prisma.foo.findMany` → `tx.foo.findMany` and the parallel `count` likewise (transactions serialize, so see the note in step 5).
- **Paths in code examples are illustrative** (`'common/pagination/PaginationDTO'`). Replace with your project's alias.

In this repo specifically, see `references/project-context.md` for concrete import paths, reference endpoints, and verification commands.

## When to Use

- You are adding a `@Get()` route that returns a list or collection.
- You are adding/modifying a DTO whose name ends in `ListResponseDTO` / `QueryDTO`, or a Zod schema ending in `ListResponseSchema` / `QuerySchema`.
- You see a controller method returning `Promise<X[]>`, `Promise<{ items: ... }>`, `Promise<{ users: ... }>`, etc.
- You are reviewing or refactoring a list endpoint and need to decide if it conforms.

**Do NOT use for:** detail routes (`@Get(':id')`, `@Get('me')`), count/boolean endpoints, non-HTTP service helpers, or service methods invoked only by jobs/schedulers.

## Checklist

1. **Query DTO** — colocated with the feature's other DTOs (e.g. `<feature>/dto/<Feature>DTO.ts`):

   ```ts
   import { createZodDto } from 'nestjs-zod';
   import { z } from 'zod';
   import {
     PaginationQueryBaseSchema,
     refineSkipAlignedWithLimit,
   } from 'common/pagination/PaginationDTO';

   const FooQuerySchema = refineSkipAlignedWithLimit(
     PaginationQueryBaseSchema.extend({
       search: z.string().trim().min(1).max(200).optional(),
       status: FooStatusSchema.optional().default('all'),
     }),
   );
   export class FooQueryDTO extends createZodDto(FooQuerySchema) {}
   ```

   - `.extend(...)` the **unrefined** `PaginationQueryBaseSchema`, never re-declare `skip`/`limit`, and wrap the result in `refineSkipAlignedWithLimit` (refinement-then-extend silently drops the refinement).
   - Filter fields use `.optional()`; add `.default(...)` only when there is a meaningful default.

2. **Item schema** — the single-row shape. Dates are `z.iso.datetime()` (wire format is JSON, so Prisma `Date`s arrive as ISO strings after step 5). Nullables are `.nullable()`:

   ```ts
   const FooSchema = z.object({
     id: z.number().int(),
     name: z.string(),
     createdAt: z.iso.datetime(),
     deletedAt: z.iso.datetime().nullable(),
   });
   ```

3. **Response DTO** — named class, extends the factory:

   ```ts
   export class FooListResponseDTO extends createPaginatedResponseDto(FooSchema) {}
   ```

   Never hand-roll a `{ items, pagination }` schema — the factory exists to keep the OpenAPI `$ref` stable.

4. **Controller** — accept the query DTO, annotate the return type, declare `@ApiExtraModels` + `@ApiResponse`:

   ```ts
   import { ApiExtraModels, ApiOperation, ApiResponse, ApiTags } from '@nestjs/swagger';

   @ApiTags('foos')
   @ApiExtraModels(FooQueryDTO)
   @Controller('foos')
   export class FoosController {
     @Get()
     @ApiOperation({ summary: 'List foos, paginated' })
     @ApiResponse({ status: 200, description: 'Paginated list of foos', type: FooListResponseDTO })
     async list(@Query() query: FooQueryDTO): Promise<FooListResponseDTO> {
       return this.foosService.findAll({
         skip: query.skip,
         limit: query.limit,
         search: query.search,
         status: query.status,
       });
     }
   }
   ```

   - `@ApiExtraModels(FooQueryDTO)` registers **only the query DTO** — see V6 below for why. Do **not** also list the response DTO there.
   - `Promise<FooListResponseDTO>` return annotation is mandatory; without it, shape drift slips past `tsc`.

5. **Service** — explicit named return type, parallel fetch, ISO dates:

   ```ts
   import { buildPaginatedResponse } from 'common/pagination/paginated-response';
   import { FooListResponseDTO } from './dto/FooDTO';

   interface FindAllFoosParams {
     skip?: number;
     limit?: number;
     search?: string;
     status?: 'active' | 'archived' | 'all';
   }

   async findAll(params: FindAllFoosParams): Promise<FooListResponseDTO> {
     const { skip, limit, search, status = 'all' } = params;
     const where: Prisma.FooWhereInput = { /* ... */ };

     const [ rows, total ] = await Promise.all([
       this.prisma.foo.findMany({ where, skip, take: limit, orderBy: { createdAt: 'desc' } }),
       this.prisma.foo.count({ where }),
     ]);

     const items = rows.map((r) => ({
       ...r,
       createdAt: r.createdAt.toISOString(),
       deletedAt: r.deletedAt?.toISOString() ?? null,
     }));

     return buildPaginatedResponse({ items, total, skip, limit });
   }
   ```

   - Return type is the named DTO class, not `PaginatedResponse<{...inline...}>` — an inline generic lets the schema and the returned shape drift silently.
   - Count and fetch **in parallel** with `Promise.all`. Inside a `$transaction` callback, Prisma interactive transactions serialize by default, so there's no parallelism to gain — keep the two `await tx.foo.findMany(...)` / `await tx.foo.count(...)` calls sequential and still call `buildPaginatedResponse` with the results.
   - Convert every Prisma `Date` field with `.toISOString()`. Nullable: `value?.toISOString() ?? null`.
   - Always forward `skip` and `limit` to `buildPaginatedResponse` so `pagination.page` is computed correctly.

## Quick Reference

| Concern | Required | Forbidden |
|---|---|---|
| Query DTO | `PaginationQueryBaseSchema.extend({...})` + `refineSkipAlignedWithLimit(...)` | hand-rolled `z.object({ skip, limit })`, raw `@Query('skip')`/`@Query('limit')` primitives, `page`-based query |
| Response DTO | `class FooListResponseDTO extends createPaginatedResponseDto(FooSchema) {}` | `{ foos: z.array(...) }`, `{ items, total }`, `Promise<FooDTO[]>` |
| Service return | `Promise<FooListResponseDTO>` | `Promise<PaginatedResponse<{...inline...}>>`, missing return type, `Promise<{ foos, total }>` |
| Envelope | `buildPaginatedResponse({ items, total, skip, limit })` | hand-rolled `{ items, pagination: {...} }` |
| Dates | `.toISOString()` (+ `?? null` for nullable) | raw Prisma `Date` objects on the wire |
| OpenAPI | `@ApiExtraModels(FooQueryDTO)` **(query only)** + `@ApiResponse({ type: FooListResponseDTO })` | response DTO inside `@ApiExtraModels`, `type: [FooDTO]` array shorthand, missing decorators |

## Violations (V1–V7)

Use these IDs in PR/commit messages so follow-up audits are greppable.

- **V1 — No envelope**: controller returns a bare array (`Promise<FooDTO[]>`) or bare `{ foos: [...] }`. Fix: wrap in `FooListResponseDTO` + `buildPaginatedResponse`.
- **V2 — Hand-rolled response DTO**: `z.object({ foos: z.array(...) })` or similar. Fix: `createPaginatedResponseDto(FooSchema)`.
- **V3 — Non-standard query**: doesn't extend `PaginationQueryBaseSchema`, or uses `@Query('skip')`/`@Query('limit')` primitives, or forgets `refineSkipAlignedWithLimit`. Also: a `page` field on the query (pagination is skip-based; `page` is a response field only). Fix: rebuild around the base schema.
- **V4 — Inline service return type**: `Promise<PaginatedResponse<{...}>>` instead of the named DTO class. Fix: import and annotate with the named DTO.
- **V5 — Raw `Date` leak**: Prisma `Date` objects reach the controller. Fix: `.toISOString()` in `items.map(...)`.
- **V6 — Wrong OpenAPI decorators**: this is the single canonical rule for the `@ApiExtraModels` tripwire.
  - `@Query()` parameter DTOs are inlined as route params by `@nestjs/swagger`, so the query DTO's nested `createZodDto` schema is **never** registered as a named component unless the controller declares `@ApiExtraModels(FooQueryDTO)`. Missing it ⇒ generated client types regenerate with a missing `$ref` or `unknown` shape.
  - `@ApiResponse({ type: FooListResponseDTO })` already registers the response DTO. Listing it **also** in `@ApiExtraModels` is redundant noise — strip it.
  - `type: [FooDTO]` array shorthand is forbidden on list routes — use the named `FooListResponseDTO`.
- **V7 — No `buildPaginatedResponse`**: service constructs `{ items, pagination: {...} }` by hand. Fix: call the helper.

## Red Flags (stop and re-read)

- `Promise<X[]>` on a controller method annotated `@Get()` that lists things.
- `Promise<PaginatedResponse<{ id: number; ... }>>` in a service file.
- `z.object({ foos: z.array(...) })` or `z.object({ items: ..., total: ... })` without the `pagination` metadata object.
- `createdAt: x.createdAt,` (no `.toISOString()`) inside an `items.map(...)` that will be serialized.
- `@Query('skip') skip?: number, @Query('limit') limit?: number` as primitive params on a list route.
- `total: items.length` when a filter / `where` is in play (should come from `prisma.foo.count({ where })`).
- `type: [FooDTO]` inside `@ApiResponse`.
- `page` as a field on a query schema.

## Workflow When Fixing an Offending Endpoint

1. Read the controller method, its service method, and the matching DTO file together — they must move as one unit.
2. Rewrite the DTO file first (query + item schema + response DTO).
3. Update the service signature and body (return type, `buildPaginatedResponse`, `.toISOString()`).
4. Update the controller (parameter type, return type annotation, decorators).
5. Typecheck the backend — typing must pass before anything else.
6. Lint the touched files.
7. Regenerate the OpenAPI spec and inspect it — the endpoint should now expose named `$ref`s for both query and response.
8. Update or add a service-level test for the list method.

---

**See also:**
- `references/canonical-helpers.md` — drop-in source for the four helpers.
- `references/project-context.md` — this repo's concrete paths, reference endpoints, and verification commands (ignore if you're using this skill outside the originating repo).
