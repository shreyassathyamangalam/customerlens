"""Pre-built Cypher queries for segment analytics."""

SEGMENT_AOV = """
MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment),
      (c)-[:PLACED]->(o:Order)
RETURN s.name AS segment, round(avg(o.total_value), 2) AS avg_order_value,
       count(o) AS total_orders
ORDER BY avg_order_value DESC
"""

INACTIVE_CHAMPIONS = """
MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment {name: 'Champions'}),
      (c)-[:PLACED]->(o:Order)
WITH c, s, max(date(o.date)) AS last_order
WHERE duration.between(last_order, date()).days > $days_inactive
RETURN c.id, c.name, c.city, last_order
ORDER BY last_order ASC
"""

CROSS_SELL_PAIRS = """
MATCH (c:Customer)-[:BELONGS_TO]->(s:Segment {name: $segment}),
      (c)-[:PLACED]->(o:Order)-[:CONTAINS]->(p1:Product),
      (o)-[:CONTAINS]->(p2:Product)
WHERE p1.id < p2.id
RETURN p1.name AS product_a, p2.name AS product_b, count(*) AS co_purchases
ORDER BY co_purchases DESC LIMIT 20
"""
