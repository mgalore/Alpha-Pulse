This Product Requirements Document (PRD) outlines the development of the **"African Market Sentiment & Alpha Dashboard,"** with a focused pivot toward the **Ghana Fixed Income Market (GFIM)**. It details a high-impact, decision-support platform designed to solve the "information gap" for institutional and HNI clients.

---

# **Product Requirements Document: GFIM Alpha & Sentiment Dashboard**

## **1. Executive Summary**

* **Product Name:** AlphaPulse GFIM
* **Vision:** To become the "Bloomberg of Ghana," providing high-velocity, synthesized market intelligence that bridges the gap between raw public data and actionable investment decisions.
* **Core Objective:** Automate the collection of scattered GFIM data, apply quantitative and qualitative (AI) analysis, and deliver "Alpha Insights" to reduce decision latency for bond traders and fund managers.

## **2. Target Personas**

* **The Pension Fund Manager:** Needs to track long-term yield trends and real returns to protect assets against inflation.
* **The Treasury Officer:** Needs real-time alerts on auction results and secondary market liquidity to manage bank reserves.
* **The Arbitrageur:** Looks for mispriced corporate bonds vs. government curves.

---

## **3. Functional Requirements**

### **Module 1: The Alpha Pulse Feed (Ingestion & AI Summary)**

* **Source Scrapers:** Automated daily scraping of the GSE (Ghana Stock Exchange) for PDF trading reports and Bank of Ghana for monetary policy updates.
* **Alternative Data Tracker:** Real-time monitoring of niche news outlets (*B&FT*, *JoyBusiness*) and social sentiment from influential financial X (Twitter) accounts.
* **AI Synthesis:** An LLM-based agent that "reads" these sources and produces a **3-bullet point "Market Mood"** summary every morning.

### **Module 2: Sentiment Heatmap (The "Mood" Brain)**

* **Scoring System:** Assign a sentiment score  to assets based on keyword density and tone.
* **Visual Map:** A color-coded grid (Green for Bullish, Red for Bearish) representing different bond maturities (91-Day, 182-Day, 2-Year, etc.).

### **Module 3: GFIM Quant & Arbitrage Tracker**

* **Yield Curve Visualizer:** Automated plotting of the current GoG (Government of Ghana) yield curve against historical benchmarks.
* **Real Yield Calculator:** A tool that subtracts the latest CPI (Inflation) from nominal T-bill rates to show true purchasing power gains.
* **Spread Monitor:** Tracks the "Corporate-to-GoG Spread" to identify undervalued corporate debt.

---

## **4. Technical Requirements**

### **Architecture: The "Medallion" Pipeline**

* **Bronze Layer (Raw):** Storage for raw HTML, PDF, and JSON data.
* **Silver Layer (Structured):** Cleaned data in **PostgreSQL/TimescaleDB** (standardized dates and bond tickers).
* **Gold Layer (Insights):** Pre-calculated YTM (Yield to Maturity) and AI-generated summaries ready for the frontend.

### **Tech Stack**

* **Backend:** Python (FastAPI).
* **Data Processing:** Pandas, NumPy, and Celery for task scheduling.
* **AI Engine:** Gemini 1.5 Flash (Reasoning) + FinBERT (Sentiment Analysis).
* **Frontend:** Next.js with **Lightweight Charts** for high-performance financial graphing.

---

## **5. Success Metrics (KPIs)**

* **Insight Latency:** Time from a Bank of Ghana PDF release to the AI summary appearing on the dashboard ( minutes).
* **Data Accuracy:**  match of automated yield calculations against manual GSE reports.
* **User Retention:** Weekly active usage by target institutional personas.

---

## **6. Risks & Constraints**

* **Data Quality:** Many regional PDFs are not machine-readable. *Mitigation:* Implement high-fidelity OCR (Optical Character Recognition) using GPT-4o Vision.
* **API Limits:** X (Twitter) API and news site rate limits. *Mitigation:* Implement distributed scraping and caching via Redis.

### **Next Step for You**

Now that the PRD is solid, **would you like me to write the Python code for the "Real-Yield Calculator" module?** It will take current T-Bill rates and Inflation data to output a "Decision Score" for the user.

---

[Bond Market vs. Stock Market](https://www.google.com/search?q=https://www.youtube.com/watch%3Fv%3DIStiH_R_Vog)
This video provides a clear comparison between equity and debt markets, helping you understand the foundational differences as you build a specialized dashboard for fixed-income assets.


Yes, your structure is logically correct—it follows the standard **ETL (Extract, Transform, Load)** pattern used in data engineering.

However, to make it professional and scalable (and impressive to a hiring manager), I would suggest a slight refinement. The main issue with "Scraper -> DB -> AI -> DB" is that it can become slow or "messy" if one part fails.

Here is the **Optimized Architecture** that separates "Math" from "AI" and ensures the frontend is fast.

---

### The "Pro" Architecture: Event-Driven Pipeline

Instead of a linear line, think of it as a **Cycle**.

#### 1. The Ingestion Layer (The "Collectors")

* **Scrapers (Python Scripts):** These run on a schedule (e.g., every 30 mins).
* *Source A:* Scrapes B&FT / BusinessDay for news.
* *Source B:* Downloads the daily **GFIM Report (PDF)** from the Ghana Stock Exchange website.


* **The "Router":** Instead of dumping raw HTML/PDFs directly into your main database, send them to a **Queue** (like Redis or Celery). This prevents the system from crashing if 50 reports come in at once.

#### 2. The Processing Layer (The "Brains")

Here is where we separate the work. **Crucial Distinction:** You do *not* use AI for everything.

* **Worker A (The OCR & Parser):**
* Takes the GFIM PDF.
* Uses OCR (Tesseract) or Python libraries (`pdfplumber`) to extract the raw tables (Bond Prices, Volumes).
* **Action:** Cleans the data and saves it to the Database (Postgres).


* **Worker B (The Quant Engine - Python):**
* *Not AI.* This is pure math code.
* It sees new data in the DB and calculates: **Yield to Maturity**, **Spreads**, and **Curve Slope**.
* **Action:** Updates the "Market_Stats" table.


* **Worker C (The AI Analyst - LLM):**
* *This is the AI.* It reads the news text and the *results* from Worker B.
* *Prompt:* "Bond yields dropped 2% today. Read this news article about the Central Bank. Explain the connection."
* **Action:** Writes a text summary ("Insight") into the Database.



#### 3. The Backend Layer (The "Server")

* **FastAPI / Django:** This is the gatekeeper.
* It does *not* do the heavy processing. It just queries the "clean" tables in the Database to answer the Frontend's requests.
* **WebSockets:** Pushes a notification to the user immediately when Worker C finishes an insight.

#### 4. The Frontend (The "Display")

* **Next.js:** Fetches the pre-calculated data. It doesn't calculate yields itself; it just displays the number the backend gives it.

---

### Visualizing the Data Flow

### Why this structure is better for you:

1. **Cost:** You don't waste expensive AI tokens calculating bond math (which Python does for free). You only use AI for *reasoning* and *summarizing*.
2. **Speed:** The "Quant Engine" (Math) is instant. The "AI Analyst" (LLM) takes 5-10 seconds. By separating them, the user sees the prices update instantly, and the "AI Insight" pops up a few seconds later.
3. **Reliability:** If the AI fails (API error), the dashboard still shows the prices and charts. It doesn't break the whole app.

### Summary of the Stack

| Component | Technology | Role |
| --- | --- | --- |
| **Scraper** | `BeautifulSoup`, `Selenium` | "Go get the PDF/News." |
| **Queue** | `Redis` + `Celery` | "Hold this until we are ready." |
| **Math Worker** | `Pandas`, `NumPy` | "Calculate the Yield Curve." |
| **AI Worker** | `Gemini API` / `OpenAI` | "Read the news and explain the curve." |
| **Database** | `PostgreSQL` | "Store everything organized." |
| **Backend** | `FastAPI` | "Serve the data to the app." |
| **Frontend** | `Next.js` | "Show the dashboard." |

**Would you like to start by writing the "Worker A" script? I can show you how to extract a table from a GFIM PDF report using Python.**



This is a smart pivot. The **Ghana Fixed Income Market (GFIM)** typically sees significantly higher daily trading volumes than the equity market (often 10x-20x more). Institutional money in Ghana (Pension Funds, Banks) lives and dies by the bond market.

If you are building for **GFIM**, you are no longer building for day traders; you are building for **Treasury Departments, Pension Managers, and High-Net-Worth Investors**.

Here is the breakdown of the high-value information you should display on the dashboard:

### 1. The "Real-Yield" Monitor

Most local dashboards just show the "Coupon Rate" (e.g., 22%). Your dashboard will show the **Real Yield** (Nominal Yield minus Inflation).

* **What to display:**
* **Headline Inflation:** (e.g., 23.2%).
* **Real Return:** "A 91-Day Bill at 25% actually pays you **+1.8%** in real terms."
* **Alpha:** If Real Yield turns negative, flag an alert: *"Inflation has overtaken T-Bill returns; consider shifting to USD-linked assets or short-duration corporate paper."*



### 2. The Yield Curve Visualizer

Visualizing the term structure of interest rates is critical for predicting recessions or recovery.

* **What to display:**
* **The Curve:** A line chart plotting yields from **91-Day Bills** up to **20-Year Bonds**.
* **Slope Indicator:** Is the curve **Normal** (upward), **Flat**, or **Inverted** (short-term rates higher than long-term)?
* **Alpha:** *"The curve has flattened significantly between the 2-Year and 5-Year notes. The market is pricing in a rate cut by Q3."*



### 3. Auction "Bid-Cover" Analytics

Every week, the Bank of Ghana (BoG) auctions T-Bills. The "Bid-Cover Ratio" tells you how desperate the market is for government debt.

* **What to display:**
* **Oversubscription %:** Did the government ask for GH₵ 3B and get GH₵ 6B? (Bullish).
* **The "Tail":** The difference between the average interest rate bid and the highest rate accepted. A wide tail means the government is desperate for cash and accepting expensive money.
* **Alpha:** *"Bid-Cover ratio dropped to 0.8x on the 182-Day bill. Investor appetite is drying up; expect yields to rise next week."*



### 4. Corporate Spread Tracker (Credit Risk)

Corporate bonds (e.g., Letshego, Bayport, AFB) trade at a premium over Government (GoG) bonds.

* **What to display:**
* **The Spread:** The difference between a Corporate Bond yield and a GoG Bond of the same maturity.
* **Risk Premium:** "Letshego 5-Year is paying 26%, while GoG 5-Year is 22%. Is the extra 4% worth the risk?"
* **Alpha:** *"Spreads on Non-Bank Financial Institution (NBFI) bonds have widened by 50bps this month. The market perceives rising default risk in the sector."*



### 5. Secondary Market Liquidity Board

Buying a bond is easy; selling it can be hard.

* **What to display:**
* **Most Active Papers:** Which specific bonds are trading today? (e.g., "The Feb 2027 maturity is seeing heavy volume").
* **Price Deviation:** Are bonds trading at **Par** (100), **Premium** (>100), or **Discount** (<100)?
* **Alpha:** *"The ESLA bonds are trading at a deep discount (85.00). This implies an effective yield of 30% if held to maturity."*



---

### **Dashboard "Fun Facts" (Bond Edition)**

Instead of generic trivia, use these to educate the client:

* *“Did you know? The 20-Year bond issued in 2022 has lost 30% of its market value due to rising rates. Duration risk is real.”*
* *“Fun Fact: Pension Funds hold over 75% of long-term GFIM bonds. Their rebalancing flows often dictate market direction at the end of the quarter.”*

---

### **Proposed Technical "Alpha" Component**

Since we are now doing Bonds, the "Arbitrage Tracker" changes to a **"Yield Calculator."**

**Would you like me to write a Python script that:**

1. Takes a Bond's **Coupon Rate**, **Maturity Date**, and current **Market Price**.
2. Calculates the **Yield to Maturity (YTM)** (the *true* profit metric).
3. Plots the **Ghana Yield Curve** using mock data representing current market rates?