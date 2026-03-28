## Phase 1: Database Layer

- [ ] Create `src/db/schema.ts` with TypeORM entity definitions
- [ ] Add User, Project, and Task entities
- [ ] Set up connection pool in `src/db/connection.ts`

## Phase 2: Authentication System

- [ ] Implement JWT token generation in `src/auth/jwt.ts`
- [ ] Create login endpoint `src/routes/auth.ts`
- [ ] Add middleware for token verification `src/middleware/auth.ts`

## Phase 3: Core API Routes

- [ ] Build CRUD for projects in `src/routes/projects.ts`
- [ ] Build CRUD for tasks in `src/routes/tasks.ts`
- [ ] Add pagination helpers `src/utils/pagination.ts`

## Phase 4: Frontend Components

- [ ] Create ProjectList component `src/components/ProjectList.tsx`
- [ ] Create TaskBoard component `src/components/TaskBoard.tsx`
- [ ] Wire up API calls in `src/api/client.ts`

## Phase 5: Testing & CI

- [ ] Write unit tests for auth module `test/auth.test.ts`
- [ ] Write integration tests for API `test/api.test.ts`
- [ ] Add GitHub Actions workflow `.github/workflows/ci.yml`
