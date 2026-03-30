---
name: "Data Query"
description: "Livins房源数据库schema与SQL查询策略"
---

# Data Query

## When to Use
- 用户提出任何数据分析需求时
- 需要生成SQL查询房源数据

## Database Schema

> Source: /home/lee/white_forest/whiteforest/backend/data_service/apt_postgresql_db/models.py

### buildings — 建筑信息
| 列 | 类型 | 说明 |
|----|------|------|
| id | BigInteger PK | |
| address | String | 地址 |
| city, state, zipcode | String | |
| borough | String | 区: Manhattan, Brooklyn, Queens, Bronx, Staten Island |
| neighborhood | String | 社区 |
| location | Geography(POINT) | PostGIS坐标 |
| building_name | String | 建筑名 |
| property_type | String | 物业类型 |
| built_in | Integer | 建造年份 |
| building_amenities | JSONB | 设施 (key-value) |
| pet_policy | String | 宠物政策 |
| nearby_schools | JSONB | 附近学校 |
| rating | Float | 评分 |
| google_rating, google_rating_count | Float, Integer | Google评分 |
| website, phone, email | String | 联系方式 |
| landlord_id | BigInteger | 房东ID |
| mobility_score | JSONB | 出行评分 |

### listings — 房源列表
| 列 | 类型 | 说明 |
|----|------|------|
| id | BigInteger PK | |
| building_id | BigInteger FK → buildings.id | |
| status | String | open / closed |
| unit_number | String | 房间号 |
| floor | Integer | 楼层 |
| price | Integer | 月租金($) |
| bedrooms | Integer | 卧室数 (0=Studio) |
| bathrooms | Float | 卫生间数 |
| sqft | Float | 面积(sqft) |
| type | String | 租赁类型 |
| description | Text | 描述 |
| listed_at | Date | 上架日期 |
| available_from | Date | 可入住日期 |
| closed_at | Date | 下架日期 |
| days_on_market | Integer | 在架天数 |
| agent_name | String | 经纪人 |
| image_urls | JSONB | 图片URL列表 |
| unite_amenities | JSONB | 房间设施 |
| **折扣字段** | | |
| min_lease_months | Float | 最短租期(月) |
| discount_free_rent_months | Float | 免租月数 |
| discount_free_rent_amount | Float | 免租金额($) |
| security_deposit_waived | Boolean | 押金减免 |
| application_fee_waived | Boolean | 申请费减免 |
| no_broker_fee | Boolean | 无中介费 |
| max_discount | Float | 最大折扣总额($) |
| discount_pct_off | Float | 折扣百分比 |
| discount_description | String | 折扣描述 |
| ranking_score | Float | 排名分数(内部) |
| low_income | Boolean | 低收入住房 |

### ml_listings — ML特征 (1:1 listings)
| 列 | 类型 | 说明 |
|----|------|------|
| listing_id | BigInteger FK → listings.id (unique) | |
| has_floor_to_ceiling_windows | Boolean | 落地窗 |
| has_balcony | Boolean | 阳台 |
| has_hardwood_floors | Boolean | 硬木地板 |
| has_bathtub | Boolean | 浴缸 |
| overall_decoration_style | String | 装修风格 |
| overall_condition_level | Integer 1-5 | 房况评级 |
| aesthetic_score | Float 0-10 | 美学评分 |
| windows_direction | JSONB | 窗户朝向列表 |

### building_isochrones — 通勤范围 (1:N buildings)
| 列 | 类型 | 说明 |
|----|------|------|
| building_id | BigInteger FK → buildings.id | |
| transportation_mode | String | walking / transit / driving |
| duration_minutes | Integer | 15 / 30 / 60 |
| polygon | Geography(MULTIPOLYGON) | 可达范围 |

### 表关系
```
buildings ──1:N──► listings ──1:1──► ml_listings
    │
    └──1:N──► building_isochrones
```

## SQL 查询规范

所有数据通过 `query_database(sql)` Tool 执行只读 SQL。API 层自动做安全校验（AST解析+白名单+超时）。

### 允许的操作
- SELECT（含 JOIN、子查询、聚合、窗口函数）
- 只允许查询以上4张表：buildings, listings, ml_listings, building_isochrones

### 禁止的操作
- INSERT, UPDATE, DELETE, DROP, CREATE, ALTER（API层自动拒绝）

### 常用 JOIN 路径
```sql
-- 房源+建筑（价格+区域分析）
listings l JOIN buildings b ON l.building_id = b.id

-- 房源+ML特征（装修/美学+价格分析）
listings l JOIN ml_listings ml ON ml.listing_id = l.id

-- 完整链：建筑+房源+ML特征
buildings b
  JOIN listings l ON l.building_id = b.id
  JOIN ml_listings ml ON ml.listing_id = l.id

-- 建筑+通勤范围
buildings b JOIN building_isochrones bi ON bi.building_id = b.id
```

### 常用查询模式（已验证可直接使用）

#### 1. 各区租金汇总
```sql
SELECT
    INITCAP(LOWER(b.borough)) AS borough,
    COUNT(*) AS total_listings,
    AVG(l.price)::int AS avg_price,
    MIN(l.price) AS min_price,
    MAX(l.price) AS max_price
FROM listings l
JOIN buildings b ON l.building_id = b.id
WHERE l.status = 'open'
    AND LOWER(b.borough) IN ('manhattan','brooklyn','queens','bronx','staten island')
GROUP BY LOWER(b.borough)
ORDER BY avg_price DESC
```

#### 2. 按户型分析（bedrooms 分组）
```sql
SELECT
    INITCAP(LOWER(b.borough)) AS borough,
    l.bedrooms,
    COUNT(*) AS count,
    AVG(l.price)::int AS avg_price
FROM listings l
JOIN buildings b ON l.building_id = b.id
WHERE l.status = 'open'
    AND LOWER(b.borough) IN ('manhattan','brooklyn','queens','bronx','staten island')
GROUP BY LOWER(b.borough), l.bedrooms
ORDER BY LOWER(b.borough), l.bedrooms
```
> 注意：用 `l.bedrooms` 直接分组（0=Studio, 1=1BR, 2=2BR...），不需要 CASE WHEN。在结果里再映射名称。

#### 3. 月度租金趋势
```sql
SELECT
    DATE_TRUNC('month', l.listed_at)::date AS month,
    INITCAP(LOWER(b.borough)) AS borough,
    AVG(l.price)::int AS avg_price,
    COUNT(*) AS count
FROM listings l
JOIN buildings b ON l.building_id = b.id
WHERE l.status = 'open'
    AND LOWER(b.borough) IN ('manhattan','brooklyn','queens','bronx','staten island')
    AND l.listed_at >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY 1, LOWER(b.borough)
ORDER BY 1, borough
```

#### 4. 折扣分析
```sql
SELECT
    INITCAP(LOWER(b.borough)) AS borough,
    COUNT(*) AS total_listings,
    COUNT(CASE WHEN l.max_discount > 0 THEN 1 END) AS discounted_count,
    ROUND(100.0 * COUNT(CASE WHEN l.max_discount > 0 THEN 1 END) / COUNT(*), 1) AS discount_pct,
    AVG(CASE WHEN l.max_discount > 0 THEN l.max_discount END)::int AS avg_discount
FROM listings l
JOIN buildings b ON l.building_id = b.id
WHERE l.status = 'open'
    AND LOWER(b.borough) IN ('manhattan','brooklyn','queens','bronx','staten island')
GROUP BY LOWER(b.borough)
ORDER BY discount_pct DESC
```

#### 5. ML 特征 vs 价格
```sql
SELECT
    ml.overall_condition_level AS condition_level,
    COUNT(*) AS count,
    AVG(l.price)::int AS avg_price,
    ROUND(AVG(ml.aesthetic_score)::numeric, 1) AS avg_aesthetic
FROM ml_listings ml
JOIN listings l ON ml.listing_id = l.id
WHERE l.status = 'open'
GROUP BY ml.overall_condition_level
ORDER BY condition_level
```

#### 6. Top N 最便宜/最贵
```sql
SELECT l.id, b.borough, b.neighborhood, l.price, l.bedrooms, l.sqft
FROM listings l JOIN buildings b ON l.building_id = b.id
WHERE l.status = 'open' AND LOWER(b.borough) = 'manhattan'
ORDER BY l.price ASC LIMIT 10
```

### SQL 编写规则
- 用上面的模式直接改参数，不要自己发明新的 SQL 结构
- 不要用 CASE WHEN 做分类——在 GROUP BY 用原始字段，分类名称在 Python 代码里映射
- 一次查询最多返回几百行，不要全表扫描
- 查询返回的结果直接是 `{"columns": [...], "rows": [...], "row_count": N}`
- 如果查询返回了预期数据，就继续下一步，不要重复查类似的 SQL

### 注意事项
- `borough` 在 buildings 表，`price`/`bedrooms` 在 listings 表，跨表查询需要 JOIN
- `listed_at` 是 Date 类型，用 `DATE_TRUNC` 做时间聚合
- `bedrooms = 0` 表示 Studio
- `status = 'open'` 是在架房源，分析时通常只看 open 状态
- JSONB 字段（amenities等）用 `->>`/`@>` 操作符查询
- `neighborhood` 字段可能为 NULL 或不够详细，优先用 `borough` 做区域分析
- 查询结果为空不代表 SQL 有错，可能确实没有符合条件的数据——不要无意义地重试相同查询
- **borough 大小写不一致**：数据库中同时存在 `Manhattan` 和 `manhattan`，查询时必须用 `LOWER(borough)` 或 `ILIKE`
- **数据库包含非 NYC 数据**（LA, Chicago, NJ 等），NYC 分析时需加 `WHERE LOWER(b.borough) IN ('manhattan','brooklyn','queens','bronx','staten island')`

## NYC 区域映射

用户提到的区域名称需要映射到 `buildings.borough` 或 `buildings.neighborhood` 字段。

### Borough 映射
| 用户说 | borough 值 |
|--------|-----------|
| "New York" / "NYC" / "NY" | 查全部5个区 |
| "Manhattan" / "曼哈顿" | Manhattan |
| "Brooklyn" / "布鲁克林" | Brooklyn |
| "Queens" / "皇后区" | Queens |
| "Bronx" / "布朗克斯" | Bronx |
| "Staten Island" / "斯坦顿岛" | Staten Island |

### 常见 Neighborhood 缩写
| 缩写 | 全称 | Borough |
|------|------|---------|
| UES | Upper East Side | Manhattan |
| UWS | Upper West Side | Manhattan |
| LIC | Long Island City | Queens |
| Bed-Stuy | Bedford-Stuyvesant | Brooklyn |
| FiDi | Financial District | Manhattan |
| DUMBO | DUMBO | Brooklyn |
| Hell's Kitchen | Hell's Kitchen | Manhattan |

### 预算 → 区域建议
| 预算 | 推荐区域 |
|------|----------|
| $4,000+/月 | Chelsea, Greenwich Village, UES, DUMBO, Williamsburg |
| $2,500–$4,000/月 | Hell's Kitchen, East Village, Astoria, Park Slope |
| $2,500以下/月 | Crown Heights, Ridgewood, Washington Heights, Sunset Park |

### 查询示例
```sql
-- 按 neighborhood 分析（注意可能有 NULL）
SELECT b.neighborhood, AVG(l.price)::int AS avg_price, COUNT(*) AS cnt
FROM listings l JOIN buildings b ON l.building_id = b.id
WHERE b.borough = 'Manhattan' AND b.neighborhood IS NOT NULL
GROUP BY b.neighborhood
ORDER BY avg_price DESC

-- 按缩写查询
WHERE b.neighborhood ILIKE '%upper east%'
```
