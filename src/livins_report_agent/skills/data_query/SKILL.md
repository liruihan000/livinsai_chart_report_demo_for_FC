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

### 常用查询模式

| 分析需求 | SQL 模式 |
|----------|----------|
| 租金趋势 | `SELECT DATE_TRUNC('month', listed_at), AVG(price) ... GROUP BY 1` |
| 区域对比 | `SELECT borough, AVG(price), MIN(price), MAX(price) ... GROUP BY borough` |
| 折扣分析 | `SELECT borough, COUNT(*), AVG(max_discount) ... WHERE max_discount > 0 GROUP BY borough` |
| ML特征相关性 | `SELECT condition_level, AVG(aesthetic_score), AVG(price) ... GROUP BY condition_level` |
| Top N | `SELECT ... ORDER BY price ASC LIMIT N` |

### 注意事项
- `borough` 在 buildings 表，`price`/`bedrooms` 在 listings 表，跨表查询需要 JOIN
- `listed_at` 是 Date 类型，用 `DATE_TRUNC` 做时间聚合
- `bedrooms = 0` 表示 Studio
- `status = 'open'` 是在架房源，分析时通常只看 open 状态
- JSONB 字段（amenities等）用 `->>`/`@>` 操作符查询
