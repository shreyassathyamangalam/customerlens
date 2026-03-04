# Node Labels

| Label      | Key Properties                                          |
|------------|---------------------------------------------------------|
| Customer   | id, name, age, gender, city, join_date, rfm_segment     |
| Order      | id, date, total_value, channel                          |
| Product    | id, name, price, brand                                  |
| Category   | id, name                                                |
| Segment    | id, name                                                |
| Campaign   | id, name, type, start_date                              |

# Relationships

| Relationship              | From       | To        | Properties          |
|---------------------------|------------|-----------|---------------------|
| PLACED                    | Customer   | Order     | —                   |
| CONTAINS                  | Order      | Product   | quantity, unit_price|
| BELONGS_TO (product)      | Product    | Category  | —                   |
| BELONGS_TO (customer)     | Customer   | Segment   | since               |
| RESPONDED_TO              | Customer   | Campaign  | response_date       |
| TARGETS                   | Campaign   | Segment   | —                   |
