-- ============================================
-- MATERIALIZED VIEWS for "Где мои деньги"
-- Оптимизация аналитических запросов
-- ============================================

-- ============================================
-- 1. Materialized View: Ежемесячная статистика по пользователям
-- ============================================
DROP MATERIALIZED VIEW IF EXISTS monthly_user_stats_mv CASCADE;

CREATE MATERIALIZED VIEW monthly_user_stats_mv AS
SELECT 
    user_id,
    DATE_TRUNC('month', created_at) as month,
    COUNT(*) as total_transactions,
    SUM(CASE WHEN transaction_type = 'INCOME' THEN amount ELSE 0 END) as total_income,
    SUM(CASE WHEN transaction_type = 'EXPENSE' THEN amount ELSE 0 END) as total_expense,
    SUM(CASE WHEN transaction_type = 'INCOME' THEN amount ELSE -amount END) as net_balance,
    AVG(CASE WHEN transaction_type = 'INCOME' THEN amount ELSE NULL END) as avg_income,
    AVG(CASE WHEN transaction_type = 'EXPENSE' THEN amount ELSE NULL END) as avg_expense,
    MIN(created_at) as first_transaction,
    MAX(created_at) as last_transaction
FROM transaction_views
GROUP BY user_id, DATE_TRUNC('month', created_at);

-- Уникальный индекс для быстрого поиска
CREATE UNIQUE INDEX idx_mums_user_month ON monthly_user_stats_mv (user_id, month);

-- Индекс для поиска по дате
CREATE INDEX idx_mums_month ON monthly_user_stats_mv (month);

-- Индекс для поиска по балансу
CREATE INDEX idx_mums_balance ON monthly_user_stats_mv (net_balance DESC);


-- ============================================
-- 2. Materialized View: Топ категорий по расходам
-- ============================================
DROP MATERIALIZED VIEW IF EXISTS top_categories_mv CASCADE;

CREATE MATERIALIZED VIEW top_categories_mv AS
SELECT 
    user_id,
    category_id,
    category_name,
    total_expense,
    total_income,
    current_balance,
    budget_percentage,
    RANK() OVER (PARTITION BY user_id ORDER BY total_expense DESC) as expense_rank,
    RANK() OVER (PARTITION BY user_id ORDER BY total_income DESC) as income_rank,
    CASE 
        WHEN budget_percentage > 0 AND total_income > 0 
        THEN (total_expense / (total_income * budget_percentage / 100)) * 100
        ELSE 0 
    END as budget_usage_percentage
FROM category_statistics_views
WHERE total_expense > 0 OR total_income > 0;

-- Индексы для топ категорий
CREATE UNIQUE INDEX idx_tcm_user_category ON top_categories_mv (user_id, category_id);
CREATE INDEX idx_tcm_expense_rank ON top_categories_mv (user_id, expense_rank);
CREATE INDEX idx_tcm_income_rank ON top_categories_mv (user_id, income_rank);
CREATE INDEX idx_tcm_budget_usage ON top_categories_mv (user_id, budget_usage_percentage DESC);


-- ============================================
-- 3. Materialized View: Дневной баланс пользователя (тренды)
-- ============================================
DROP MATERIALIZED VIEW IF EXISTS daily_balance_trend_mv CASCADE;

CREATE MATERIALIZED VIEW daily_balance_trend_mv AS
WITH daily_totals AS (
    SELECT 
        user_id,
        DATE(created_at) as day,
        SUM(CASE WHEN transaction_type = 'INCOME' THEN amount ELSE 0 END) as daily_income,
        SUM(CASE WHEN transaction_type = 'EXPENSE' THEN amount ELSE 0 END) as daily_expense
    FROM transaction_views
    GROUP BY user_id, DATE(created_at)
)
SELECT 
    user_id,
    day,
    daily_income,
    daily_expense,
    daily_income - daily_expense as daily_net,
    SUM(daily_income - daily_expense) OVER (PARTITION BY user_id ORDER BY day) as cumulative_balance,
    AVG(daily_income - daily_expense) OVER (PARTITION BY user_id ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as avg_7day_net,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY day DESC) as recency
FROM daily_totals
ORDER BY user_id, day DESC;

-- Индексы для дневного баланса
CREATE UNIQUE INDEX idx_dbt_user_day ON daily_balance_trend_mv (user_id, day);
CREATE INDEX idx_dbt_recency ON daily_balance_trend_mv (user_id, recency);
CREATE INDEX idx_dbt_cumulative ON daily_balance_trend_mv (user_id, cumulative_balance DESC);


-- ============================================
-- 4. Materialized View: Предупреждения по бюджету
-- ============================================
DROP MATERIALIZED VIEW IF EXISTS budget_warnings_mv CASCADE;

CREATE MATERIALIZED VIEW budget_warnings_mv AS
SELECT 
    user_id,
    category_id,
    category_name,
    total_expense,
    budget_percentage,
    CASE 
        WHEN total_income > 0 THEN (total_expense / (total_income * budget_percentage / 100)) * 100
        ELSE 0
    END as budget_usage,
    CASE 
        WHEN total_income > 0 AND (total_expense / (total_income * budget_percentage / 100)) * 100 >= 80 THEN 'WARNING'
        WHEN total_income > 0 AND (total_expense / (total_income * budget_percentage / 100)) * 100 >= 100 THEN 'CRITICAL'
        ELSE 'OK'
    END as warning_level,
    current_balance,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY (total_expense / (total_income * budget_percentage / 100)) DESC) as overspend_rank
FROM category_statistics_views
WHERE budget_percentage > 0 AND total_income > 0;

-- Индексы для предупреждений
CREATE INDEX idx_bwm_user ON budget_warnings_mv (user_id, warning_level);
CREATE INDEX idx_bwm_usage ON budget_warnings_mv (user_id, budget_usage DESC);
CREATE INDEX idx_bwm_overspend ON budget_warnings_mv (user_id, overspend_rank);


-- ============================================
-- 5. Materialized View: Сравнение год к году
-- ============================================
DROP MATERIALIZED VIEW IF EXISTS yoy_comparison_mv CASCADE;

CREATE MATERIALIZED VIEW yoy_comparison_mv AS
WITH yearly_stats AS (
    SELECT 
        user_id,
        EXTRACT(YEAR FROM created_at) as year,
        EXTRACT(MONTH FROM created_at) as month,
        SUM(CASE WHEN transaction_type = 'INCOME' THEN amount ELSE 0 END) as month_income,
        SUM(CASE WHEN transaction_type = 'EXPENSE' THEN amount ELSE 0 END) as month_expense
    FROM transaction_views
    GROUP BY user_id, EXTRACT(YEAR FROM created_at), EXTRACT(MONTH FROM created_at)
)
SELECT 
    user_id,
    year,
    month,
    month_income,
    month_expense,
    month_income - month_expense as month_net,
    LAG(month_income, 12) OVER (PARTITION BY user_id ORDER BY year, month) as prev_year_income,
    LAG(month_expense, 12) OVER (PARTITION BY user_id ORDER BY year, month) as prev_year_expense,
    CASE 
        WHEN LAG(month_income, 12) OVER (PARTITION BY user_id ORDER BY year, month) > 0
        THEN ((month_income - LAG(month_income, 12) OVER (PARTITION BY user_id ORDER BY year, month)) / 
              LAG(month_income, 12) OVER (PARTITION BY user_id ORDER BY year, month)) * 100
        ELSE 0
    END as income_growth_percent,
    CASE 
        WHEN LAG(month_expense, 12) OVER (PARTITION BY user_id ORDER BY year, month) > 0
        THEN ((month_expense - LAG(month_expense, 12) OVER (PARTITION BY user_id ORDER BY year, month)) / 
              LAG(month_expense, 12) OVER (PARTITION BY user_id ORDER BY year, month)) * 100
        ELSE 0
    END as expense_growth_percent
FROM yearly_stats
ORDER BY user_id, year DESC, month DESC;

-- Индексы для YoY сравнения
CREATE UNIQUE INDEX idx_yoy_user_year_month ON yoy_comparison_mv (user_id, year, month);
CREATE INDEX idx_yoy_growth ON yoy_comparison_mv (user_id, income_growth_percent DESC);


-- ============================================
-- Функции для обновления Materialized Views
-- ============================================

-- Функция обновления всех материализованных представлений
CREATE OR REPLACE FUNCTION refresh_all_materialized_views()
RETURNS TEXT AS $$
DECLARE
    view_name TEXT;
    refresh_start TIMESTAMP;
    refresh_end TIMESTAMP;
    duration INTERVAL;
BEGIN
    refresh_start := NOW();
    
    -- Список всех материализованных представлений
    FOR view_name IN 
        SELECT matviewname 
        FROM pg_matviews 
        WHERE schemaname = 'public'
    LOOP
        RAISE NOTICE 'Refreshing %...', view_name;
        EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I', view_name);
    END LOOP;
    
    refresh_end := NOW();
    duration := refresh_end - refresh_start;
    
    RETURN format('All materialized views refreshed successfully. Duration: %s', duration);
END;
$$ LANGUAGE plpgsql;


-- Функция обновления конкретного представления по расписанию
CREATE OR REPLACE FUNCTION refresh_monthly_stats_mv()
RETURNS TRIGGER AS $$
BEGIN
    -- Обновляем только если изменились данные за последний месяц
    IF NEW.created_at > (NOW() - INTERVAL '31 days') THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_user_stats_mv;
        REFRESH MATERIALIZED VIEW CONCURRENTLY daily_balance_trend_mv;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- Триггер для автоматического обновления при новых транзакциях
DROP TRIGGER IF EXISTS trg_refresh_mv_on_transaction ON transaction_views;

CREATE TRIGGER trg_refresh_mv_on_transaction
AFTER INSERT OR UPDATE ON transaction_views
FOR EACH STATEMENT
EXECUTE FUNCTION refresh_monthly_stats_mv();


-- ============================================
-- Вспомогательные функции для работы с MV
-- ============================================

-- Функция получения последнего обновления MV
CREATE OR REPLACE FUNCTION get_mv_last_refresh(view_name TEXT)
RETURNS TIMESTAMP AS $$
DECLARE
    last_refresh TIMESTAMP;
BEGIN
    SELECT pg_stat_user_tables.last_vacuum INTO last_refresh
    FROM pg_stat_user_tables
    WHERE relname = view_name;
    
    RETURN last_refresh;
END;
$$ LANGUAGE plpgsql;


-- Функция проверки актуальности MV
CREATE OR REPLACE FUNCTION is_mv_outdated(view_name TEXT, max_age_hours INT DEFAULT 24)
RETURNS BOOLEAN AS $$
DECLARE
    last_refresh TIMESTAMP;
BEGIN
    SELECT pg_stat_user_tables.last_vacuum INTO last_refresh
    FROM pg_stat_user_tables
    WHERE relname = view_name;
    
    RETURN last_refresh IS NULL OR 
           last_refresh < (NOW() - (max_age_hours || ' hours')::INTERVAL);
END;
$$ LANGUAGE plpgsql;


-- ============================================
-- Примеры запросов к Materialized Views
-- ============================================

-- 1. Получить месячную статистику пользователя
-- SELECT * FROM monthly_user_stats_mv 
-- WHERE user_id = 'user-001' 
-- ORDER BY month DESC 
-- LIMIT 12;

-- 2. Получить топ-5 расходов пользователя
-- SELECT * FROM top_categories_mv 
-- WHERE user_id = 'user-001' AND expense_rank <= 5;

-- 3. Получить предупреждения по бюджету
-- SELECT * FROM budget_warnings_mv 
-- WHERE user_id = 'user-001' AND warning_level IN ('WARNING', 'CRITICAL');

-- 4. Получить динамику баланса за последние 30 дней
-- SELECT * FROM daily_balance_trend_mv 
-- WHERE user_id = 'user-001' AND recency <= 30 
-- ORDER BY day;

-- 5. Получить рост доходов год к году
-- SELECT * FROM yoy_comparison_mv 
-- WHERE user_id = 'user-001' 
-- ORDER BY year DESC, month DESC 
-- LIMIT 12;


-- ============================================
-- Настройка автоматического обновления (через pg_cron)
-- ============================================

-- Если установлен pg_cron, можно настроить автоматическое обновление:
-- 
-- UPDATE cron.job SET schedule = '0 1 * * *' WHERE jobname = 'refresh_mv';
-- 
-- Или через расширение:
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- 
-- SELECT cron.schedule('refresh-mv', '0 2 * * *', 
--     'SELECT refresh_all_materialized_views();'
-- );


-- ============================================
-- Мониторинг размера Materialized Views
-- ============================================

SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as indexes_size
FROM pg_tables
WHERE tablename LIKE '%_mv'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;


-- ============================================
-- Очистка и пересоздание всех MV
-- ============================================

-- Функция для полного пересоздания всех MV
CREATE OR REPLACE FUNCTION recreate_all_materialized_views()
RETURNS TEXT AS $$
BEGIN
    DROP MATERIALIZED VIEW IF EXISTS monthly_user_stats_mv CASCADE;
    DROP MATERIALIZED VIEW IF EXISTS top_categories_mv CASCADE;
    DROP MATERIALIZED VIEW IF EXISTS daily_balance_trend_mv CASCADE;
    DROP MATERIALIZED VIEW IF EXISTS budget_warnings_mv CASCADE;
    DROP MATERIALIZED VIEW IF EXISTS yoy_comparison_mv CASCADE;
    
    -- Пересоздаём все MV (нужно выполнить весь скрипт заново)
    RETURN 'All materialized views dropped. Run the full script to recreate them.';
END;
$$ LANGUAGE plpgsql;