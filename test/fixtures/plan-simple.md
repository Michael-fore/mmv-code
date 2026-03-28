## Phase 1: Setup Database Schema

- [ ] Create migration file `src/db/migrations/001_users.sql`
- [ ] Define users table with id, email, name, created_at columns
- [ ] Add unique constraint on email

## Phase 2: Implement API Endpoints

- [ ] Create route handler `src/routes/users.ts`
- [ ] Implement GET /users endpoint
- [ ] Implement POST /users endpoint
- [x] Add input validation middleware
