-- export_training.sql
-- Dumps the three flat files train_baseline.py / compare_v7.py read.
--
-- Run against Supabase project allen-qc (ref knaeexnlyfjgpowihcel) with psql:
--
--     psql "%SUPABASE_DB_URL%" -v outdir=C:/EE/ml/data -f export_training.sql
--
-- (psql wants forward slashes even on Windows. Create C:\EE\ml\data first.)
--
-- DELIBERATELY NOT EXPORTED, and this is the whole leakage argument:
--   bid_state_avg_prices, bid_geo_prices, bid_qty_curves, bid_ls_ratios
-- Every one of those was derived from all 620 contracts, holdout included.
-- Feeding them to a model trained on a subset of those same contracts leaks the
-- test set into training. train_baseline.py recomputes what it needs from the
-- training fold only. compare_v7.py does export the rule tables (rules.psv)
-- because it has to reproduce v7's arithmetic, and it says so in its header.
--
-- Nothing here contains engineer_unit_price. It is null on all but 574
-- fixed-price adjustment lines, so there is no item-level EE to learn; the
-- target is log(low_bid_unit_price) and the EE only enters at contract level.

\set ON_ERROR_STOP on

-- 1. contracts.tsv --------------------------------------------------------
-- One row per contract. `ci` is a dense 1..620 surrogate so the line file can
-- carry a short join key. Everything here is known before bids are opened
-- except engineer_estimate and low_bid, which are the targets.
\copy (WITH c AS (SELECT p.contract_id, dense_rank() OVER (ORDER BY p.contract_id) AS ci, p.letting_date, p.work_type, upper(trim(p.county)) AS county, lpad(regexp_replace(coalesce(p.district,''), '[^0-9]', '', 'g'), 2, '0') AS dist, coalesce(gp.pod_id,'') AS pod, p.n_items, p.length_miles, p.n_bidders, p.engineer_estimate, p.low_bid FROM bid_projects p LEFT JOIN bid_geo_pods gp ON gp.county = upper(trim(p.county))) SELECT ci, contract_id, letting_date, coalesce(work_type,''), county, dist, pod, n_items, length_miles, n_bidders, engineer_estimate, low_bid FROM c ORDER BY ci) TO :'outdir'/contracts.tsv WITH (FORMAT csv, DELIMITER E'\t', HEADER false)

-- 2. lines.tsv ------------------------------------------------------------
-- One row per priced bid item (21,383 of 21,717 carry a low_bid_unit_price).
-- Tabs and newlines are stripped from free text so the file stays a clean TSV.
\copy (WITH c AS (SELECT contract_id, dense_rank() OVER (ORDER BY contract_id) AS ci FROM bid_projects) SELECT c.ci, i.bid_code, i.quantity, coalesce(i.unit,''), coalesce(replace(replace(i.section, chr(9), ' '), chr(10), ' '),''), coalesce(i.binder_grade,''), CASE WHEN i.fixed_price THEN 1 ELSE 0 END, i.low_bid_unit_price, coalesce(replace(replace(i.description, chr(9), ' '), chr(10), ' '),'') FROM bid_items i JOIN c ON c.contract_id = i.contract_id WHERE i.low_bid_unit_price IS NOT NULL ORDER BY c.ci, i.bid_code) TO :'outdir'/lines.tsv WITH (FORMAT csv, DELIMITER E'\t', HEADER false)

-- 3. prices.psv -----------------------------------------------------------
-- Monthly binder (PG 64-22) and fuel series. Exogenous market data, published
-- monthly by KYTC and not derived from any contract outcome, so using it at the
-- letting month is not a leak. train_baseline.py forward-fills: the series can
-- lag the letting calendar by a month or two.
\copy (SELECT 'B|'||to_char(month,'YYYY-MM')||'|'||grade||'|'||price_per_ton FROM bid_binder_prices WHERE month >= '2021-01-01' UNION ALL SELECT 'F|'||to_char(month,'YYYY-MM')||'||'||price_per_gal FROM bid_fuel_prices WHERE month >= '2021-01-01' ORDER BY 1) TO :'outdir'/prices.psv WITH (FORMAT csv, DELIMITER '~', HEADER false, QUOTE E'\b')

-- 4. rules.psv ------------------------------------------------------------
-- v7's rule constants. Used ONLY by compare_v7.py to reproduce v7's arithmetic.
-- train_baseline.py never reads this file. These stay full-history-fitted, which
-- leaves the leak-free v7 baseline slightly generous to v7 -- see README.
\copy (SELECT 'AC|'||bid_code_pattern||'|'||ac_pct FROM bid_ac_content UNION ALL SELECT 'QC|'||bid_code||'|'||beta||'|'||q_ref FROM bid_qty_curves UNION ALL SELECT 'LS|'||bid_code||'|'||cat||'|'||pct_of_s FROM bid_ls_ratios ORDER BY 1) TO :'outdir'/rules.psv WITH (FORMAT csv, DELIMITER '~', HEADER false, QUOTE E'\b')

-- 5. v7_pred.tsv ----------------------------------------------------------
-- v7's current published predictions, so compare_v7.py can show the
-- as-published column next to the leak-free one.
\copy (SELECT contract_id, cat, ee, pred FROM bid_backtest_v7 WHERE ee > 0 AND pred > 0 ORDER BY contract_id) TO :'outdir'/v7_pred.tsv WITH (FORMAT csv, DELIMITER E'\t', HEADER false)

\echo 'exported contracts.tsv lines.tsv prices.psv rules.psv v7_pred.tsv'
