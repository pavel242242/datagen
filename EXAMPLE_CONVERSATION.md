# Example Conversation: Generating a Schema

This shows what a typical conversation looks like when using the Datagen schema generation prompt.

---

## Example 1: E-commerce Dataset

**User:** *[Pastes the prompt from SCHEMA_GENERATION_PROMPT.md]*

**LLM:** Now let's start! What kind of dataset do you need?

**User:** I need an e-commerce dataset with customers, products, and orders.

**LLM:** Great! Let me ask a few clarifying questions:

1. How many customers and products would you like? (e.g., 500 customers, 200 products)
2. Should orders have line items (multiple products per order)?
3. What time period should the orders cover?
4. Any specific fields you need? (e.g., customer demographics, product categories, order status)

**User:**
- 500 customers, 200 products
- Yes, orders should have line items
- Orders from Jan 2024 to Dec 2024
- Add customer country, product category and price, order status

**LLM:** Perfect! Here's your Datagen schema:

```json
{
  "version": "1.0",
  "metadata": {
    "name": "E-commerce Platform",
    "description": "E-commerce with customers, products, orders, and line items"
  },
  "timeframe": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-12-31T23:59:59Z",
    "freq": "H"
  },
  "constraints": {
    "foreign_keys": [
      {"from": "order.customer_id", "to": "customer.customer_id"},
      {"from": "order_item.order_id", "to": "order.order_id"},
      {"from": "order_item.product_id", "to": "product.product_id"}
    ]
  },
  "nodes": [
    {
      "id": "customer",
      "kind": "entity",
      "pk": "customer_id",
      "rows": 500,
      "columns": [
        {"name": "customer_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
        {"name": "email", "type": "string", "generator": {"faker": {"method": "email"}}},
        {"name": "name", "type": "string", "generator": {"faker": {"method": "name"}}},
        {"name": "country", "type": "string", "generator": {"choice": {"choices": ["US", "UK", "CA", "AU", "DE"], "weights": [0.4, 0.2, 0.15, 0.15, 0.1]}}},
        {"name": "signup_date", "type": "datetime", "generator": {"datetime_series": {"within": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"}, "freq": "D"}}}
      ]
    },
    {
      "id": "product",
      "kind": "entity",
      "pk": "product_id",
      "rows": 200,
      "columns": [
        {"name": "product_id", "type": "int", "generator": {"sequence": {"start": 1000, "step": 1}}},
        {"name": "name", "type": "string", "generator": {"faker": {"method": "word"}}},
        {"name": "category", "type": "string", "generator": {"choice": {"choices": ["Electronics", "Clothing", "Home", "Books"], "weights": [0.3, 0.3, 0.25, 0.15]}}},
        {"name": "price", "type": "float", "generator": {"distribution": {"type": "lognormal", "params": {"mu": 3.5, "sigma": 0.8}, "clamp": [9.99, 999.99]}}}
      ]
    },
    {
      "id": "order",
      "kind": "fact",
      "pk": "order_id",
      "parents": ["customer"],
      "fanout": {"distribution": "poisson", "lambda": 3.5},
      "columns": [
        {"name": "order_id", "type": "int", "generator": {"sequence": {"start": 10000, "step": 1}}},
        {"name": "customer_id", "type": "int", "generator": {"lookup": {"from": "customer.customer_id"}}},
        {"name": "order_date", "type": "datetime", "generator": {"datetime_series": {"within": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"}, "freq": "H"}}},
        {"name": "status", "type": "string", "generator": {"choice": {"choices": ["pending", "processing", "shipped", "delivered", "cancelled"], "weights": [0.05, 0.1, 0.2, 0.6, 0.05]}}},
        {"name": "total_amount", "type": "float", "generator": {"distribution": {"type": "lognormal", "params": {"mu": 4.2, "sigma": 0.6}, "clamp": [20.0, 2000.0]}}}
      ]
    },
    {
      "id": "order_item",
      "kind": "fact",
      "pk": "order_item_id",
      "parents": ["order"],
      "fanout": {"distribution": "poisson", "lambda": 2.5},
      "columns": [
        {"name": "order_item_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
        {"name": "order_id", "type": "int", "generator": {"lookup": {"from": "order.order_id"}}},
        {"name": "product_id", "type": "int", "generator": {"lookup": {"from": "product.product_id"}}},
        {"name": "quantity", "type": "int", "generator": {"distribution": {"type": "poisson", "params": {"lambda": 1.8}, "clamp": [1, 10]}}},
        {"name": "unit_price", "type": "float", "generator": {"distribution": {"type": "lognormal", "params": {"mu": 3.5, "sigma": 0.8}, "clamp": [9.99, 999.99]}}}
      ]
    }
  ]
}
```

Save this to `ecommerce.json` and run:
```bash
datagen generate ecommerce.json --seed 42 -o output
```

---

## Example 2: SaaS Subscription Tracking

**User:** I need to track SaaS subscriptions with users, plans, and subscription events.

**LLM:** Got it! A few questions:

1. How many users and subscription plans?
2. Should subscriptions have state transitions (trial → active → cancelled)?
3. Should there be payment/billing records?
4. Time period to cover?

**User:**
- 200 users, 3 plans (starter/pro/enterprise)
- Yes, track state changes
- Yes, include monthly payments
- Jan-Dec 2024

**LLM:** Here's your Datagen schema:

```json
{
  "version": "1.0",
  "metadata": {
    "name": "SaaS Subscription Tracker",
    "description": "Track users, plans, subscriptions, and payments"
  },
  "timeframe": {
    "start": "2024-01-01T00:00:00Z",
    "end": "2024-12-31T23:59:59Z",
    "freq": "D"
  },
  "constraints": {
    "foreign_keys": [
      {"from": "subscription.user_id", "to": "user.user_id"},
      {"from": "subscription.plan_id", "to": "plan.plan_id"},
      {"from": "payment.subscription_id", "to": "subscription.subscription_id"}
    ]
  },
  "nodes": [
    {
      "id": "user",
      "kind": "entity",
      "pk": "user_id",
      "rows": 200,
      "columns": [
        {"name": "user_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
        {"name": "email", "type": "string", "generator": {"faker": {"method": "email"}}},
        {"name": "company", "type": "string", "generator": {"faker": {"method": "company"}}},
        {"name": "signup_date", "type": "datetime", "generator": {"datetime_series": {"within": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"}, "freq": "D"}}}
      ]
    },
    {
      "id": "plan",
      "kind": "entity",
      "pk": "plan_id",
      "rows": 3,
      "columns": [
        {"name": "plan_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
        {"name": "name", "type": "string", "generator": {"choice": {"choices": ["Starter", "Professional", "Enterprise"]}}},
        {"name": "monthly_price", "type": "float", "generator": {"choice": {"choices": [29.0, 99.0, 299.0]}}}
      ]
    },
    {
      "id": "subscription",
      "kind": "fact",
      "pk": "subscription_id",
      "parents": ["user"],
      "fanout": {"distribution": "poisson", "lambda": 1.2},
      "columns": [
        {"name": "subscription_id", "type": "int", "generator": {"sequence": {"start": 1000, "step": 1}}},
        {"name": "user_id", "type": "int", "generator": {"lookup": {"from": "user.user_id"}}},
        {"name": "plan_id", "type": "int", "generator": {"lookup": {"from": "plan.plan_id"}}},
        {"name": "status", "type": "string", "generator": {"choice": {"choices": ["trial", "active", "paused", "cancelled"], "weights": [0.15, 0.6, 0.1, 0.15]}}},
        {"name": "start_date", "type": "datetime", "generator": {"datetime_series": {"within": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"}, "freq": "D"}}}
      ]
    },
    {
      "id": "payment",
      "kind": "fact",
      "pk": "payment_id",
      "parents": ["subscription"],
      "fanout": {"distribution": "poisson", "lambda": 8.0},
      "columns": [
        {"name": "payment_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
        {"name": "subscription_id", "type": "int", "generator": {"lookup": {"from": "subscription.subscription_id"}}},
        {"name": "amount", "type": "float", "generator": {"distribution": {"type": "normal", "params": {"mu": 100, "sigma": 50}, "clamp": [20, 300]}}},
        {"name": "payment_date", "type": "datetime", "generator": {"datetime_series": {"within": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"}, "freq": "D"}}},
        {"name": "status", "type": "string", "generator": {"choice": {"choices": ["success", "failed", "pending"], "weights": [0.9, 0.05, 0.05]}}}
      ]
    }
  ]
}
```

---

## Example 3: Simple IoT Sensor Data

**User:** IoT sensor readings from devices

**LLM:** Great! Quick questions:
1. How many devices?
2. What kind of readings? (temperature, humidity, etc.)
3. How often do they report?
4. Time period?

**User:**
- 50 devices
- Temperature and humidity
- Every hour
- Last 30 days

**LLM:** Here's your schema:

```json
{
  "version": "1.0",
  "metadata": {
    "name": "IoT Sensor Network",
    "description": "Temperature and humidity readings from IoT devices"
  },
  "timeframe": {
    "start": "2024-11-01T00:00:00Z",
    "end": "2024-11-30T23:59:59Z",
    "freq": "H"
  },
  "constraints": {
    "foreign_keys": [
      {"from": "reading.device_id", "to": "device.device_id"}
    ]
  },
  "nodes": [
    {
      "id": "device",
      "kind": "entity",
      "pk": "device_id",
      "rows": 50,
      "columns": [
        {"name": "device_id", "type": "int", "generator": {"sequence": {"start": 1000, "step": 1}}},
        {"name": "location", "type": "string", "generator": {"choice": {"choices": ["Building A", "Building B", "Building C", "Warehouse"]}}},
        {"name": "device_type", "type": "string", "generator": {"choice": {"choices": ["Indoor", "Outdoor"]}}},
        {"name": "installed_at", "type": "datetime", "generator": {"datetime_series": {"within": {"start": "2024-01-01T00:00:00Z", "end": "2024-10-31T23:59:59Z"}, "freq": "D"}}}
      ]
    },
    {
      "id": "reading",
      "kind": "fact",
      "pk": "reading_id",
      "parents": ["device"],
      "fanout": {"distribution": "uniform", "min": 700, "max": 720},
      "columns": [
        {"name": "reading_id", "type": "int", "generator": {"sequence": {"start": 1, "step": 1}}},
        {"name": "device_id", "type": "int", "generator": {"lookup": {"from": "device.device_id"}}},
        {"name": "timestamp", "type": "datetime", "generator": {"datetime_series": {"within": {"start": "2024-11-01T00:00:00Z", "end": "2024-11-30T23:59:59Z"}, "freq": "H"}}},
        {"name": "temperature", "type": "float", "generator": {"distribution": {"type": "normal", "params": {"mu": 22.0, "sigma": 3.0}, "clamp": [15.0, 30.0]}}},
        {"name": "humidity", "type": "float", "generator": {"distribution": {"type": "normal", "params": {"mu": 50.0, "sigma": 10.0}, "clamp": [30.0, 80.0]}}}
      ]
    }
  ]
}
```

---

## Tips for Better Conversations

**Be specific about:**
- **Scale**: "500 users" not "some users"
- **Relationships**: "Orders have line items" vs "Orders reference products"
- **Time periods**: Actual dates help (Jan-Dec 2024)
- **Key fields**: List important attributes you need

**The LLM will infer:**
- Appropriate data types (email → string, price → float)
- Realistic distributions (prices → lognormal, counts → poisson)
- Sensible defaults (row counts, fanout rates)

**You can refine:**
- Ask for changes: "Can you add a status field to orders?"
- Request adjustments: "Make the price range $10-$500"
- Fix issues: "The datetime needs to be UTC with Z suffix"

The goal is a natural conversation that results in a working schema!
