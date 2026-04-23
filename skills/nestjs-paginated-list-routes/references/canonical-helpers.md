# Canonical Helper Implementations

Reference source for the four helpers `SKILL.md` assumes exist. Only `zod` (v4) and `nestjs-zod` are hard dependencies. Copy these files into your project if you don't already have equivalents; adjust import paths to match your own layout.

## `common/pagination/PaginationDTO.ts`

```ts
import { createZodDto } from 'nestjs-zod';
import { z } from 'zod';
import type { ZodTypeAny } from 'zod';

/* Constants ------------------------------------------- */
export const PAGINATION_DEFAULT_SKIP = 0;
export const PAGINATION_DEFAULT_LIMIT = 20;
export const PAGINATION_MIN_LIMIT = 1;
export const PAGINATION_MAX_LIMIT = 100;

/* Pagination Meta ------------------------------------- */
export const PaginationMetaSchema = z.object({
  page: z.number().int().min(1)
    .describe('Current page number (1-indexed)'),
  limit: z.number().int().min(PAGINATION_MIN_LIMIT)
    .describe('Effective page size applied by the server (may differ from the requested limit if the server cap was hit)'),
  total: z.number().int().min(0)
    .describe('Total number of items matching the query'),
  totalPages: z.number().int().min(1)
    .describe('Total number of pages (always >= 1, even when total is 0)'),
});

export class PaginationMetaDTO extends createZodDto(PaginationMetaSchema) {}

/* Pagination Query ------------------------------------ */
/**
 * Base pagination query shape (pre-refinement). Modules that need to extend
 * the pagination query with additional filter fields should extend THIS
 * object (via `.extend({...})`) and then apply `refineSkipAlignedWithLimit`
 * to preserve the `skip % limit === 0` invariant.
 */
export const PaginationQueryBaseSchema = z.object({
  skip: z.coerce.number().int().min(0)
    .default(PAGINATION_DEFAULT_SKIP)
    .describe('Number of records to skip'),
  limit: z.coerce.number().int()
    .min(PAGINATION_MIN_LIMIT)
    .max(PAGINATION_MAX_LIMIT)
    .default(PAGINATION_DEFAULT_LIMIT)
    .describe(`Maximum number of records to return (${PAGINATION_MIN_LIMIT}-${PAGINATION_MAX_LIMIT})`),
});

export const refineSkipAlignedWithLimit = <
  T extends z.ZodType<{ skip: number; limit: number }>,
>(schema: T) => schema.refine(
  ({ skip, limit }) => skip % limit === 0,
  {
    message: '`skip` must be a multiple of `limit` so the returned page number is unambiguous',
    path: [ 'skip' ],
  },
);

export const PaginationQuerySchema = refineSkipAlignedWithLimit(PaginationQueryBaseSchema);
export class PaginationQueryDTO extends createZodDto(PaginationQuerySchema) {}

/* Paginated Response factory -------------------------- */
export const createPaginatedResponseSchema = <TItem extends ZodTypeAny>(
  itemSchema: TItem,
) => z.object({
  items: z.array(itemSchema).describe('Items on the current page'),
  pagination: PaginationMetaSchema.describe('Pagination metadata'),
});

export const createPaginatedResponseDto = <TItem extends ZodTypeAny>(
  itemSchema: TItem,
) => createZodDto(createPaginatedResponseSchema(itemSchema));
```

## `common/pagination/paginated-response.ts`

```ts
import {
  PAGINATION_DEFAULT_LIMIT,
  PAGINATION_DEFAULT_SKIP,
} from './PaginationDTO';
import type { PaginationMetaDTO } from './PaginationDTO';

interface BuildPaginatedResponseParams<T> {
  items: T[];
  total: number;
  skip?: number;
  limit?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMetaDTO;
}

/**
 * Wrap an already-fetched slice into the canonical pagination envelope.
 * `limit` is echoed back as `effectiveLimit`; callers should have pre-validated
 * `limit` against `PaginationQueryDTO` (which caps it at `PAGINATION_MAX_LIMIT`).
 * A non-positive `limit` falls back to the default to avoid division by zero.
 */
export const buildPaginatedResponse = <T>({
  items,
  total,
  skip = PAGINATION_DEFAULT_SKIP,
  limit = PAGINATION_DEFAULT_LIMIT,
}: BuildPaginatedResponseParams<T>): PaginatedResponse<T> => {
  const effectiveLimit = limit > 0 ? limit : PAGINATION_DEFAULT_LIMIT;
  const page = Math.floor(skip / effectiveLimit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / effectiveLimit));

  return {
    items,
    pagination: {
      page,
      limit: effectiveLimit,
      total,
      totalPages,
    },
  };
};
```

## Design notes (derived-field policy)

- Only `totalPages` is emitted (clamped to `>= 1` even when `total === 0`).
- `hasNext` / `hasPrevious` are **not** emitted — they are one-liner derivations on the client (`page < totalPages`, `page > 1`). Keeping the envelope minimal avoids redundant server-computed state.
- The `skip % limit === 0` refinement is enforced by the query schema so the emitted `page` is always an honest 1-indexed boundary.
