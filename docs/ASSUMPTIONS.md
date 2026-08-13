# Slice 0 assumptions

These are prototype choices, not product claims.

1. Evidence reliability weights in `data/ontology/reliability.yaml` are starting values, not measured truth.
2. Local Postgres is exposed on host port **5433** to avoid colliding with an existing 5432 service.
3. Ontology primary keys are UUIDv5(slug) so seed is idempotent across machines.
4. PostgreSQL enum types are stored as varchar (`native_enum=False` equivalent) to keep Alembic simple.
5. The first Alembic revision creates tables from SQLAlchemy metadata. Later slices should add explicit diffs.
6. Slice 0 catalog is small and uses official docs URLs, or `url_status: unavailable` with a null URL. It is not the final 100–200 resource set.
7. Gap-engine weights and half-life in `data/ontology/gap_engine.yaml` are prototype priors.
8. `satisfied_max_gap` is a near-target band, not a declaration that the target is met.
9. Frontend `next build` skips ESLint until a real UI exists.
