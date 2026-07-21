CREATE TABLE IF NOT EXISTS dim_company (
  company_id BIGSERIAL PRIMARY KEY,
  ticker VARCHAR(20) UNIQUE NOT NULL,
  cik VARCHAR(20),
  company_name TEXT,
  sector TEXT,
  industry TEXT
);
CREATE TABLE IF NOT EXISTS fact_market_price (
  ticker VARCHAR(20) NOT NULL,
  trade_date DATE NOT NULL,
  open DOUBLE PRECISION,
  high DOUBLE PRECISION,
  low DOUBLE PRECISION,
  close DOUBLE PRECISION,
  adjusted_close DOUBLE PRECISION,
  volume DOUBLE PRECISION,
  source TEXT,
  ingested_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (ticker, trade_date)
);
