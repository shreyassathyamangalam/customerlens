"""Pre-built Cypher queries for campaign analytics."""

CAMPAIGN_CONVERSION = """
MATCH (camp:Campaign)-[:TARGETS]->(s:Segment),
      (c:Customer)-[:RESPONDED_TO]->(camp),
      (c)-[:PLACED]->(o:Order)
WHERE date(o.date) >= date(camp.start_date)
RETURN camp.name AS campaign, s.name AS segment,
       count(DISTINCT c) AS responders,
       count(DISTINCT o) AS post_response_orders
ORDER BY responders DESC
"""
