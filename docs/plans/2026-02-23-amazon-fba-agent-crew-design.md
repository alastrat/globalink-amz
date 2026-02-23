# Amazon FBA Wholesale Agent Crew - System Design

**Date:** 2026-02-23
**Status:** Approved
**Author:** Design collaboration between user and AI

---

## Overview

An AI-powered multi-agent system that fully manages an Amazon FBA wholesale business. The system runs autonomously on a VPS, communicates with the business owner via WhatsApp, and handles everything from product discovery to financial reporting.

### Business Context

- **Seller:** Colombia-based, US LLC, existing Amazon Seller account (no sales yet)
- **Model:** Wholesale (buy from US distributors, sell on Amazon FBA)
- **Core problem:** Cannot determine which products are allowed to sell (brand gating/restrictions)
- **Budget:** Under $5K total (inventory + tooling), ~$41-67/month operating cost
- **User profile:** Business-focused (not technical), wants 10-15 min/day interaction
- **Interface:** WhatsApp for daily briefings and decisions

---

## System Architecture

```
+-------------------------------------------------------------+
|                    VPS (Hetzner CX22)                        |
|                    2 vCPU, 4GB RAM                           |
|                                                              |
|  +---------------+    +---------------------------------+    |
|  | OpenClaw /    |    |        CrewAI Engine             |    |
|  | PicoClaw      |<-->|                                 |    |
|  | (WhatsApp     |    |  +----------+ +--------------+  |    |
|  |  Gateway)     |    |  | Product  | | ASIN         |  |    |
|  +------+--------+    |  | Scout    | | Matcher      |  |    |
|         |             |  +----------+ +--------------+  |    |
|         |             |  +----------+ +--------------+  |    |
|  +------v--------+    |  | Finance  | | Market       |  |    |
|  | User on       |    |  | Analyst  | | Analyst      |  |    |
|  | WhatsApp      |    |  +----------+ +--------------+  |    |
|  +---------------+    |  +----------+ +--------------+  |    |
|                       |  | Supply   | | Restriction  |  |    |
|                       |  | Chain    | | Checker      |  |    |
|                       |  +----------+ +--------------+  |    |
|                       |  +----------+                   |    |
|                       |  | Briefing |                   |    |
|                       |  | Agent    |                   |    |
|                       |  +----------+                   |    |
|                       +-----------------+---------------+    |
|                                         |                    |
|  +--------------------------------------v-----------------+  |
|  |                    Data Layer                          |  |
|  |  SQLite DB  |  Wholesale Catalogs  |  Analysis Cache  |  |
|  +----------------------------------------------------+  |  |
+-------|--------------------------------------------------+---+
        | External APIs
        |
  +-----+-------+------------+------------+
  |             |            |            |
  v             v            v            v
+----------+ +--------+ +---------+ +----------+
| Amazon   | | Keepa  | | Claude  | | Firecrawl|
| SP-API   | | Ext.   | | API     | | API      |
| (Free)   | | (Free) | | (~$25)  | | ($16)    |
+----------+ +--------+ +---------+ +----------+
                                    +----------+
                                    | Exa API  |
                                    | (~$8)    |
                                    +----------+
```

---

## Agent Crew

### Agent 1: Product Scout
- **Goal:** Discover wholesale products worth analyzing
- **Tools:** Exa (web search), Firecrawl (site scraping)
- **LLM:** Claude Haiku (cost-efficient for repetitive discovery)
- **Workflow:** Searches wholesale directories, scrapes supplier catalogs, extracts product lists (name, UPC, wholesale price, MOQ), passes to ASIN Matcher
- **Schedule:** Daily scan + on-demand when user shares a supplier URL

### Agent 2: ASIN Matcher
- **Goal:** Match wholesale products to Amazon ASINs
- **Tools:** SP-API (Product Catalog), UPC lookup databases
- **LLM:** Claude Haiku
- **Workflow:** Takes UPC/product name from Scout, finds matching Amazon ASIN, pulls current listing data (price, BSR, category, seller count)

### Agent 3: Restriction Checker
- **Goal:** Filter out products the seller cannot list
- **Tools:** SP-API (`getListingRestrictions`)
- **LLM:** Claude Haiku
- **Workflow:** Takes ASINs, checks gating status via SP-API, filters out restricted products, flags "approval_required" products separately (some can be unlocked)

### Agent 4: Financial Analyst
- **Goal:** Calculate profitability for every ungated product
- **Tools:** SP-API (Product Fees), built-in offline fee calculator
- **LLM:** Claude Sonnet (complex financial reasoning)
- **Workflow:** Wholesale cost + Amazon selling price - (referral fee + FBA fee + prep cost + shipping) = estimated profit. Calculates ROI%, monthly profit potential.
- **Filters:** Minimum 30% ROI, minimum $3 profit per unit

### Agent 5: Market Analyst
- **Goal:** Evaluate demand strength and competitive dynamics
- **Tools:** SP-API data, Exa (market research)
- **LLM:** Claude Sonnet (nuanced market analysis)
- **Workflow:** Analyzes BSR (lower = more sales), number of FBA sellers, Buy Box dynamics, category trends. Scores each product on a demand/competition matrix.
- **Filters:** Avoids hazmat, high-return categories, products with 20+ FBA sellers

### Agent 6: Supply Chain Agent
- **Goal:** Track suppliers, prep centers, and logistics
- **Tools:** Database, Firecrawl (supplier sites), email drafts
- **LLM:** Claude Haiku
- **Workflow:** Maintains supplier database, tracks pricing changes, identifies prep centers, estimates total landed cost including prep/labeling fees. Drafts supplier outreach and negotiation emails.

### Agent 7: Daily Briefing Agent (Orchestrator)
- **Goal:** Compile insights and deliver actionable WhatsApp reports
- **Tools:** OpenClaw/PicoClaw WhatsApp gateway, all other agents' outputs
- **LLM:** Claude Sonnet (synthesis and communication)
- **Workflow:** Runs the full pipeline, ranks top 10-20 opportunities, sends formatted WhatsApp message, handles interactive replies

---

## Business Workflows

### WF1: Product Research
- **Trigger:** Daily at 6:00 AM
- **Flow:** Scout finds products -> Matcher links to Amazon -> Restriction Checker filters gated -> Finance calculates profit -> Market evaluates demand -> Briefing sends top opportunities
- **Output:** Morning WhatsApp briefing with ranked products

### WF2: Supplier Management
- **Trigger:** Weekly refresh + on-demand
- **Capabilities:** Maintain supplier database, track pricing across suppliers, draft negotiation/intro emails, monitor supplier sites for new products
- **WhatsApp commands:** `add supplier [URL]`, `quote [product]`, `draft intro [supplier]`, `negotiate [supplier] [product]`

### WF3: Order Management
- **Trigger:** Every 6 hours status check + on-demand
- **Capabilities:** Track POs from creation to delivery, monitor shipment tracking, alert on delivery to prep center, track FBA inbound shipments
- **WhatsApp commands:** `order [product] [qty] [supplier]`, `orders`, `track [PO#]`, `inbound`

### WF4: Prep Center & Shipping
- **Trigger:** Daily check
- **Capabilities:** Manage prep center relationship (labeling, poly-bagging, inspection), generate FBA shipping plans via SP-API, track processing times, calculate prep costs per unit
- **WhatsApp commands:** `prep status`, `prep costs`, `ship to fba [products]`

### WF5: Live Inventory & Buy Box Monitoring
- **Trigger:** Every 2 hours for Buy Box, daily for inventory summary
- **Capabilities:** Monitor FBA inventory levels, restock alerts, Buy Box win rate tracking, competitor pricing, repricing suggestions
- **WhatsApp commands:** `inventory`, `buybox`, `reprice [ASIN] [price]`, `restock`

### WF6: Returns & Account Health
- **Trigger:** Daily health check + immediate critical alerts
- **Capabilities:** Monitor return rates, track account health (ODR, late shipment), flag problem products (>5% return rate), monitor reviews
- **WhatsApp commands:** `returns`, `health`, `reviews [ASIN]`

### WF7: Finance & P&L
- **Trigger:** Weekly P&L report, daily profit snapshot
- **Capabilities:** Track all costs, calculate actual profit per product, P&L reports, cash flow tracking, ROI analysis, tax expense tracking
- **WhatsApp commands:** `profit`, `pnl`, `roi [product]`, `cashflow`

### WF8: Price Intelligence
- **Trigger:** Daily retail price check, every 2 hours for Amazon
- **Capabilities:** Monitor own Amazon listings (SP-API), monitor Walmart/Target (Firecrawl), detect price drops, alert on competitor undercuts, suggest repricing or discontinuation, build own price history over time
- **WhatsApp commands:** `prices`, `alert threshold [ASIN] [min_price]`, `price history [ASIN]`

---

## WhatsApp Daily Schedule

| Time | Report | Workflow |
|------|--------|----------|
| 7:00 AM | Morning Product Briefing | WF1 |
| 8:00 AM | Inventory & Buy Box Alert (if action needed) | WF5 |
| 12:00 PM | Order Status Update | WF3 |
| 6:00 PM | Daily P&L Snapshot | WF7 |
| As needed | Critical Alerts | WF6 (health), WF5 (Buy Box loss), WF8 (price drops) |

### Example WhatsApp Briefing

```
Daily FBA Opportunities - Feb 23

Top 5 Products:

1. Kitchen Gadget XYZ
   ASIN: B08XXXXX | BSR: 4,200
   Wholesale: $8.50 | Amazon: $24.99
   Fees: $9.12 | Profit: $7.37/unit
   ROI: 87% | Sellers: 4 FBA
   UNGATED | Supplier: ABC Dist.

2. Pet Toy ABC
   ...

Reply:
- "details 1" - full breakdown
- "buy 1" - draft purchase order
- "supplier 1" - supplier contact info
- "skip" - no action today
- "add supplier [url]" - add new supplier
```

---

## Technical Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Agent Framework | CrewAI (Python) | Mature multi-agent orchestration, Claude support, free/open-source |
| LLM | Claude API (Haiku + Sonnet mix) | Best reasoning, cost-effective model mixing |
| WhatsApp Gateway | OpenClaw or PicoClaw | Multi-channel AI assistant, VPS-hosted |
| Web Scraping | Firecrawl API ($16/mo Hobby) | Structured scraping of supplier and retail sites |
| Web Search | Exa API (~$5-10/mo) | AI-powered supplier and market discovery |
| Amazon Data | SP-API (free) | Official API for all Amazon operations |
| Database | SQLite (upgrade to PostgreSQL later) | Simple, no extra server |
| Task Scheduling | APScheduler (Python) | Cron-like scheduling for workflows |
| VPS | Hetzner CX22 ($5-8/mo) | 2 vCPU, 4GB RAM |
| Deployment | Docker Compose | Single command deployment, easy updates |

---

## Project Structure

```
amazon-fba-agent/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── requirements.txt
├── config/
│   ├── agents.yaml            # Agent roles, goals, LLM assignments
│   ├── filters.yaml           # Product filters (min ROI, categories)
│   └── schedules.yaml         # Workflow timing config
├── src/
│   ├── __init__.py
│   ├── main.py                # Application entry point
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── product_scout.py
│   │   ├── asin_matcher.py
│   │   ├── restriction_checker.py
│   │   ├── financial_analyst.py
│   │   ├── market_analyst.py
│   │   ├── supply_chain.py
│   │   └── briefing_agent.py
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── wf1_product_research.py
│   │   ├── wf2_supplier_management.py
│   │   ├── wf3_order_management.py
│   │   ├── wf4_prep_shipping.py
│   │   ├── wf5_inventory_buybox.py
│   │   ├── wf6_returns_health.py
│   │   ├── wf7_finance.py
│   │   └── wf8_price_intelligence.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── amazon_sp_api.py   # SP-API client wrapper
│   │   ├── firecrawl_tool.py  # Supplier/retail scraping
│   │   ├── exa_tool.py        # Web search
│   │   ├── fee_calculator.py  # Offline FBA fee calculation
│   │   └── upc_lookup.py      # UPC to ASIN mapping
│   ├── gateway/
│   │   ├── __init__.py
│   │   ├── whatsapp_handler.py    # Message routing and commands
│   │   └── message_templates.py   # Formatted report templates
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py          # SQLAlchemy models
│   │   └── migrations/
│   └── scheduler/
│       ├── __init__.py
│       └── jobs.py            # Scheduled workflow triggers
└── tests/
    ├── __init__.py
    ├── test_agents/
    ├── test_tools/
    └── test_workflows/
```

---

## Database Schema (Key Tables)

- **products** - Discovered products with wholesale pricing, UPC, name, category
- **amazon_listings** - ASIN data, BSR, current prices, seller counts, category
- **restrictions** - Gating status per ASIN for the seller account (cached, refreshed periodically)
- **profitability** - Calculated ROI, fees, margins, profit per unit
- **suppliers** - Wholesale suppliers: name, URL, contact, categories, MOQs, payment terms
- **supplier_products** - Junction: which supplier offers which product at what price
- **prep_centers** - Prep center info: name, fees per service, turnaround time
- **purchase_orders** - POs: supplier, products, qty, cost, status, tracking
- **fba_shipments** - FBA inbound shipments: status, items, destination FC
- **inventory** - Current FBA inventory levels per ASIN
- **price_history** - Historical price tracking across Amazon, Walmart, Target (our own data)
- **buybox_history** - Buy Box ownership tracking over time
- **returns** - Return data per product
- **daily_reports** - Historical daily briefings for trend analysis
- **financial_transactions** - All money in/out for P&L

---

## SP-API Permissions Required

| API | Endpoint | Workflow |
|-----|----------|----------|
| Listings Restrictions | `getListingRestrictions` | WF1 - Gating check |
| Product Fees | `getMyFeesEstimate` | WF1 - Fee calculation |
| Catalog Items | `getCatalogItem`, `searchCatalogItems` | WF1 - Product data |
| Product Pricing | `getCompetitivePricing`, `getItemOffers` | WF1, WF5, WF8 |
| FBA Inventory | `getInventorySummaries` | WF5 - Stock levels |
| FBA Inbound | Shipment creation/tracking APIs | WF4 - FBA shipments |
| Orders | `getOrders` | WF3, WF7 - Order tracking |
| Reports | Various report types | WF6, WF7 - Returns, finance |
| Notifications | `getSubscription` | WF5 - Real-time alerts |

---

## Monthly Operating Cost

| Item | Cost | Notes |
|------|------|-------|
| VPS (Hetzner CX22) | $5-8 | 2 vCPU, 4GB RAM |
| Claude API (Haiku + Sonnet) | $15-30 | Haiku for 90% of tasks |
| Firecrawl Hobby | $16 | 3,000 pages/month |
| Exa | $5-10 | Pay-as-you-go |
| Amazon SP-API | Free | All endpoints |
| Keepa Extension | Free-3 | Browser extension for manual review |
| **Total** | **$41-67/mo** | |

---

## Bootstrapping Plan

### Phase 1: Setup & First Suppliers (Week 1-2)
1. Register SP-API developer app in Seller Central
2. Provision Hetzner VPS, deploy via Docker Compose
3. Connect WhatsApp via OpenClaw/PicoClaw
4. Agent-driven supplier discovery (wholesale directories, Faire, etc.)
5. Agent-driven prep center research and comparison

### Phase 2: First Product Analysis (Week 2-3)
1. Upload first wholesale price lists from approved suppliers
2. Full pipeline: match -> gate check -> profitability -> ranking
3. Receive first real buying opportunities via WhatsApp

### Phase 3: First Purchase (Week 3-4)
1. Approve a product from daily briefing
2. System drafts purchase order
3. Place order with supplier -> ships to prep center
4. Prep center processes -> ships to FBA
5. System monitors entire pipeline

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| SP-API application rejected | Apply as self-developer (simpler than public app) |
| WhatsApp account banned (unofficial API) | Use separate WhatsApp number, not personal |
| Supplier won't sell without US address | US LLC has registered agent address |
| First product fails | Start small (10-20 units), learn before scaling |
| API costs spike | Haiku for 90% of tasks, monitor usage daily |
| Product gets gated after purchase | Always re-check gating before ordering |
| Firecrawl pages run out | Prioritize high-value scrapes, upgrade plan if revenue justifies |
