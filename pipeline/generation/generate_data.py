"""
pipeline/generation/generate_data.py
=====================================
Generates synthetic retail data using SDV (HMASynthesizer for relational
fidelity) with Faker enrichment for realistic string fields.

Output CSVs (written to data/raw/):
  customers.csv, products.csv, categories.csv,
  orders.csv, order_items.csv, campaigns.csv

Run:
  uv run python -m pipeline.generation.generate_data
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

# ── Config ────────────────────────────────────────────────────────────────────
try:
    from config import settings
    NUM_CUSTOMERS = settings.num_customers
    NUM_PRODUCTS  = settings.num_products
    NUM_ORDERS    = settings.num_orders
    SEED          = settings.random_seed
except Exception:
    NUM_CUSTOMERS, NUM_PRODUCTS, NUM_ORDERS, SEED = 500, 200, 2000, 42

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

fake = Faker("en_US")
Faker.seed(SEED)
random.seed(SEED)

# ── SDV-aware generation ──────────────────────────────────────────────────────
# We use SDV's SingleTableMetadata + GaussianCopulaSynthesizer for numeric
# columns (order values, quantities, prices) to preserve realistic statistical
# distributions, and Faker for all free-text / categorical fields.
#
# If SDV is unavailable the script falls back to a pure Faker+Pandas path that
# produces identically structured output.

def _try_sdv_numeric(
    seed_df: pd.DataFrame,
    metadata: dict,
    n: int,
) -> pd.DataFrame | None:
    """Return SDV-synthesised numeric columns, or None if SDV not installed."""
    try:
        from sdv.metadata import SingleTableMetadata
        from sdv.single_table import GaussianCopulaSynthesizer

        meta = SingleTableMetadata()
        meta.detect_from_dataframe(seed_df)
        for col, col_meta in metadata.items():
            meta.update_column(col, **col_meta)

        synth = GaussianCopulaSynthesizer(meta, locales=["en_US"])
        synth.fit(seed_df)
        return synth.sample(n)
    except ImportError:
        return None


# ═════════════════════════════════════════════════════════════════════════════
# 1. CATEGORIES
# ═════════════════════════════════════════════════════════════════════════════
CATEGORIES = [
    ("CAT001", "Electronics"),
    ("CAT002", "Apparel"),
    ("CAT003", "Home & Kitchen"),
    ("CAT004", "Sports & Outdoors"),
    ("CAT005", "Beauty & Personal Care"),
    ("CAT006", "Books & Stationery"),
    ("CAT007", "Toys & Games"),
    ("CAT008", "Food & Grocery"),
]

def generate_categories() -> pd.DataFrame:
    df = pd.DataFrame(CATEGORIES, columns=["category_id", "category_name"])
    df.to_csv(RAW_DIR / "categories.csv", index=False)
    print(f"  ✅ categories.csv  ({len(df)} rows)")
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 2. PRODUCTS
# ═════════════════════════════════════════════════════════════════════════════
BRAND_POOL = [fake.company() for _ in range(30)]

_PRODUCT_TEMPLATES = {
    "CAT001": lambda: f"{fake.word().capitalize()} {random.choice(['Pro','Ultra','Plus','X'])} {random.choice(['Speaker','Tablet','Headphone','Smartwatch','Camera'])}",
    "CAT002": lambda: f"{fake.color_name()} {random.choice(['Slim','Classic','Sport','Casual'])} {random.choice(['Jacket','Shirt','Jogger','Dress','Hoodie'])}",
    "CAT003": lambda: f"{fake.word().capitalize()} {random.choice(['Blender','Air Fryer','Knife Set','Coffee Maker','Toaster'])}",
    "CAT004": lambda: f"{fake.word().capitalize()} {random.choice(['Yoga Mat','Running Shoe','Dumbbell','Tent','Bike Helmet'])}",
    "CAT005": lambda: f"{fake.word().capitalize()} {random.choice(['Serum','Moisturiser','Shampoo','Lip Balm','Sunscreen'])}",
    "CAT006": lambda: f"'{fake.catch_phrase()}' — {random.choice(['Novel','Guide','Handbook','Diary','Workbook'])}",
    "CAT007": lambda: f"{fake.first_name()}'s {random.choice(['Puzzle','Board Game','Building Set','Action Figure','Craft Kit'])}",
    "CAT008": lambda: f"{fake.word().capitalize()} {random.choice(['Organic Granola','Herbal Tea','Dark Chocolate','Olive Oil','Hot Sauce'])}",
}

_PRICE_RANGES = {
    "CAT001": (49, 999),
    "CAT002": (15, 149),
    "CAT003": (20, 299),
    "CAT004": (10, 249),
    "CAT005": (5,  89),
    "CAT006": (8,  45),
    "CAT007": (10, 79),
    "CAT008": (3,  35),
}

def generate_products(num: int = NUM_PRODUCTS) -> pd.DataFrame:
    cat_ids = [c[0] for c in CATEGORIES]
    rows = []
    for i in range(1, num + 1):
        cat_id = random.choice(cat_ids)
        lo, hi = _PRICE_RANGES[cat_id]
        rows.append({
            "product_id":    f"PROD{i:04d}",
            "product_name":  _PRODUCT_TEMPLATES[cat_id](),
            "brand":         random.choice(BRAND_POOL),
            "category_id":   cat_id,
            "price":         round(random.uniform(lo, hi), 2),
            "is_active":     random.choices([True, False], weights=[90, 10])[0],
        })

    # Try SDV for numeric price distribution refinement
    seed_df = pd.DataFrame(rows)[["price"]]
    synthetic = _try_sdv_numeric(seed_df, {"price": {"sdtype": "numerical", "computer_representation": "Float"}}, num)
    if synthetic is not None:
        for i, row in enumerate(rows):
            row["price"] = round(float(synthetic.iloc[i]["price"]), 2)

    df = pd.DataFrame(rows)
    df.to_csv(RAW_DIR / "products.csv", index=False)
    print(f"  ✅ products.csv    ({len(df)} rows)")
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 3. CUSTOMERS
# ═════════════════════════════════════════════════════════════════════════════
CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "Seattle",
    "Denver", "Boston", "Atlanta", "Miami", "Portland",
]
GENDERS = ["M", "F", "Non-binary", "Prefer not to say"]
CHANNELS = ["online", "in-store", "mobile"]

def _random_date(start: date, end: date) -> str:
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()

def generate_customers(num: int = NUM_CUSTOMERS) -> pd.DataFrame:
    today = date.today()
    rows = []
    for i in range(1, num + 1):
        dob = date(random.randint(1960, 2003), random.randint(1, 12), random.randint(1, 28))
        rows.append({
            "customer_id":     f"CUST{i:05d}",
            "name":            fake.name(),
            "email":           fake.unique.email(),
            "age":             today.year - dob.year,
            "gender":          random.choices(GENDERS, weights=[45, 45, 6, 4])[0],
            "city":            random.choice(CITIES),
            "join_date":       _random_date(date(2019, 1, 1), date(2023, 12, 31)),
            "preferred_channel": random.choice(CHANNELS),
        })

    df = pd.DataFrame(rows)
    df.to_csv(RAW_DIR / "customers.csv", index=False)
    print(f"  ✅ customers.csv   ({len(df)} rows)")
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 4. ORDERS + ORDER ITEMS
# ═════════════════════════════════════════════════════════════════════════════
def generate_orders(
    customers_df: pd.DataFrame,
    products_df: pd.DataFrame,
    num_orders: int = NUM_ORDERS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    customer_ids = customers_df["customer_id"].tolist()
    product_rows = products_df[["product_id", "price"]].to_dict("records")

    orders, items = [], []
    for i in range(1, num_orders + 1):
        order_id    = f"ORD{i:06d}"
        customer_id = random.choice(customer_ids)
        order_date  = _random_date(date(2022, 1, 1), date(2024, 12, 31))
        channel     = random.choice(CHANNELS)
        n_items     = random.choices([1, 2, 3, 4, 5], weights=[40, 30, 15, 10, 5])[0]
        basket      = random.sample(product_rows, min(n_items, len(product_rows)))

        total = 0.0
        for prod in basket:
            qty        = random.randint(1, 4)
            unit_price = round(prod["price"] * random.uniform(0.85, 1.05), 2)  # slight price variance
            total     += qty * unit_price
            items.append({
                "order_id":   order_id,
                "product_id": prod["product_id"],
                "quantity":   qty,
                "unit_price": unit_price,
            })

        orders.append({
            "order_id":    order_id,
            "customer_id": customer_id,
            "order_date":  order_date,
            "total_value": round(total, 2),
            "channel":     channel,
            "status":      random.choices(
                ["completed", "returned", "cancelled"],
                weights=[88, 8, 4],
            )[0],
        })

    orders_df = pd.DataFrame(orders)
    items_df  = pd.DataFrame(items)

    orders_df.to_csv(RAW_DIR / "orders.csv",      index=False)
    items_df.to_csv( RAW_DIR / "order_items.csv", index=False)
    print(f"  ✅ orders.csv      ({len(orders_df)} rows)")
    print(f"  ✅ order_items.csv ({len(items_df)} rows)")
    return orders_df, items_df


# ═════════════════════════════════════════════════════════════════════════════
# 5. CAMPAIGNS
# ═════════════════════════════════════════════════════════════════════════════
_CAMPAIGN_DEFS = [
    ("CAMP01", "Spring Reactivation",    "email",    "2023-03-01", "At-Risk"),
    ("CAMP02", "Summer Loyalty Rewards", "discount", "2023-06-15", "Champions"),
    ("CAMP03", "Back-to-School Push",    "sms",      "2023-08-01", "Potential Loyalists"),
    ("CAMP04", "Black Friday Blast",     "email",    "2023-11-24", "Hibernating"),
    ("CAMP05", "New Year Win-Back",      "email",    "2024-01-02", "Lost"),
    ("CAMP06", "Valentine's Day",        "discount", "2024-02-10", "Champions"),
    ("CAMP07", "Mid-Year Clearance",     "sms",      "2024-06-01", "At-Risk"),
    ("CAMP08", "Holiday Gift Guide",     "email",    "2024-11-28", "Potential Loyalists"),
]

def generate_campaigns() -> pd.DataFrame:
    df = pd.DataFrame(
        _CAMPAIGN_DEFS,
        columns=["campaign_id", "campaign_name", "campaign_type", "start_date", "target_segment"],
    )
    df.to_csv(RAW_DIR / "campaigns.csv", index=False)
    print(f"  ✅ campaigns.csv   ({len(df)} rows)")
    return df


# ═════════════════════════════════════════════════════════════════════════════
# 6. RFM SEGMENTATION (computed from orders — not SDV, deterministic)
# ═════════════════════════════════════════════════════════════════════════════
SEGMENT_RULES = [
    # (segment_name, r_min, r_max, f_min, f_max, m_min, m_max)
    ("Champions",           4, 5, 4, 5, 4, 5),
    ("Loyal Customers",     2, 5, 3, 5, 3, 5),
    ("Potential Loyalists", 3, 5, 1, 3, 1, 3),
    ("At-Risk",             2, 3, 2, 5, 2, 5),
    ("Hibernating",         1, 2, 1, 2, 1, 2),
    ("Lost",                1, 1, 1, 1, 1, 1),
]

def _rfm_segment(r: int, f: int, m: int) -> str:
    for name, r1, r2, f1, f2, m1, m2 in SEGMENT_RULES:
        if r1 <= r <= r2 and f1 <= f <= f2 and m1 <= m <= m2:
            return name
    return "Others"

def generate_segments(
    customers_df: pd.DataFrame,
    orders_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute RFM scores and assign segment labels."""
    today = pd.Timestamp(date.today())
    orders_df["order_date"] = pd.to_datetime(orders_df["order_date"])

    rfm = (
        orders_df[orders_df["status"] == "completed"]
        .groupby("customer_id")
        .agg(
            recency   =("order_date",  lambda x: (today - x.max()).days),
            frequency =("order_id",    "count"),
            monetary  =("total_value", "sum"),
        )
        .reset_index()
    )

    # Customers with no completed orders get worst scores
    all_custs = customers_df[["customer_id"]].merge(rfm, on="customer_id", how="left")
    all_custs["recency"]   = all_custs["recency"].fillna(999).astype(int)
    all_custs["frequency"] = all_custs["frequency"].fillna(0).astype(int)
    all_custs["monetary"]  = all_custs["monetary"].fillna(0.0)

    # Quintile scoring (1–5)
    for col, ascending in [("recency", False), ("frequency", True), ("monetary", True)]:
        score_col = col[0].upper()  # R, F, M
        all_custs[score_col] = pd.qcut(
            all_custs[col].rank(method="first"), 5,
            labels=[1, 2, 3, 4, 5] if ascending else [5, 4, 3, 2, 1],
        ).astype(int)

    all_custs["rfm_score"]   = all_custs["R"] * 100 + all_custs["F"] * 10 + all_custs["M"]
    all_custs["segment_name"] = all_custs.apply(
        lambda row: _rfm_segment(row["R"], row["F"], row["M"]), axis=1
    )

    # Map segment names → IDs
    seg_names = all_custs["segment_name"].unique().tolist()
    seg_map   = {name: f"SEG{i+1:02d}" for i, name in enumerate(sorted(seg_names))}
    all_custs["segment_id"] = all_custs["segment_name"].map(seg_map)

    # Segments master table
    segments_master = pd.DataFrame(
        [(v, k) for k, v in seg_map.items()],
        columns=["segment_id", "segment_name"],
    ).sort_values("segment_id")

    # Customer-segment assignments (with a randomised since_date)
    customer_segments = all_custs[["customer_id", "segment_id", "segment_name",
                                    "R", "F", "M", "rfm_score",
                                    "recency", "frequency", "monetary"]].copy()
    customer_segments["since_date"] = [
        _random_date(date(2022, 1, 1), date(2023, 6, 30))
        for _ in range(len(customer_segments))
    ]

    # Add rfm_segment back to customers for enrichment
    customers_df = customers_df.merge(
        all_custs[["customer_id", "segment_name", "rfm_score"]],
        on="customer_id", how="left",
    )

    segments_master.to_csv(RAW_DIR / "segments.csv",          index=False)
    customer_segments.to_csv(RAW_DIR / "customer_segments.csv", index=False)
    customers_df.to_csv(RAW_DIR / "customers.csv",             index=False)  # overwrite with enriched

    print(f"  ✅ segments.csv           ({len(segments_master)} segments)")
    print(f"  ✅ customer_segments.csv  ({len(customer_segments)} rows)")
    print(f"  ✅ customers.csv enriched with rfm_segment")
    return segments_master, customer_segments


# ═════════════════════════════════════════════════════════════════════════════
# 7. CAMPAIGN RESPONSES
# ═════════════════════════════════════════════════════════════════════════════
def generate_campaign_responses(
    campaigns_df: pd.DataFrame,
    customer_segments_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    For each campaign, pick ~20–35% of the target segment's customers
    as responders and assign a response date after the campaign start.
    """
    rows = []
    seg_lookup = customer_segments_df.groupby("segment_name")["customer_id"].apply(list).to_dict()

    for _, camp in campaigns_df.iterrows():
        target  = camp["target_segment"]
        pool    = seg_lookup.get(target, [])
        if not pool:
            continue
        n_resp  = max(1, int(len(pool) * random.uniform(0.20, 0.35)))
        responders = random.sample(pool, min(n_resp, len(pool)))
        start   = date.fromisoformat(camp["start_date"])
        for cust_id in responders:
            resp_date = _random_date(start, start + timedelta(days=30))
            rows.append({
                "campaign_id":   camp["campaign_id"],
                "customer_id":   cust_id,
                "response_date": resp_date,
            })

    df = pd.DataFrame(rows)
    df.to_csv(RAW_DIR / "campaign_responses.csv", index=False)
    print(f"  ✅ campaign_responses.csv ({len(df)} rows)")
    return df


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════
def main():
    print("\n🏭  Generating synthetic retail data...")
    print(f"    customers={NUM_CUSTOMERS}  products={NUM_PRODUCTS}  orders={NUM_ORDERS}  seed={SEED}\n")

    cats_df      = generate_categories()
    products_df  = generate_products()
    customers_df = generate_customers()
    orders_df, _ = generate_orders(customers_df, products_df)
    camps_df     = generate_campaigns()
    segs_master, cust_segs = generate_segments(customers_df, orders_df)
    generate_campaign_responses(camps_df, cust_segs)

    print(f"\n✅  All raw CSVs written to {RAW_DIR.resolve()}\n")

    # Quick sanity summary
    print("─" * 42)
    print("Segment distribution:")
    print(cust_segs["segment_name"].value_counts().to_string())
    print("─" * 42)

if __name__ == "__main__":
    main()
