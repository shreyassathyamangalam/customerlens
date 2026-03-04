// ============================================================
// CustomerLens — Neo4j Constraints & Indexes
// Apply once to a fresh AuraDB instance via schema_loader.py
// All statements use IF NOT EXISTS for safe re-runs.
// ============================================================

// ── Uniqueness Constraints (also create implicit indexes) ──
CREATE CONSTRAINT customer_id_unique IF NOT EXISTS
  FOR (c:Customer) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT product_id_unique IF NOT EXISTS
  FOR (p:Product) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT order_id_unique IF NOT EXISTS
  FOR (o:Order) REQUIRE o.id IS UNIQUE;

CREATE CONSTRAINT category_id_unique IF NOT EXISTS
  FOR (c:Category) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT segment_id_unique IF NOT EXISTS
  FOR (s:Segment) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT campaign_id_unique IF NOT EXISTS
  FOR (c:Campaign) REQUIRE c.id IS UNIQUE;

// ── Additional Lookup Indexes ──────────────────────────────
CREATE INDEX customer_city IF NOT EXISTS
  FOR (c:Customer) ON (c.city);

CREATE INDEX customer_segment IF NOT EXISTS
  FOR (c:Customer) ON (c.rfm_score);

CREATE INDEX order_date IF NOT EXISTS
  FOR (o:Order) ON (o.date);

CREATE INDEX order_status IF NOT EXISTS
  FOR (o:Order) ON (o.status);

CREATE INDEX product_brand IF NOT EXISTS
  FOR (p:Product) ON (p.brand);

CREATE INDEX campaign_type IF NOT EXISTS
  FOR (c:Campaign) ON (c.type)
