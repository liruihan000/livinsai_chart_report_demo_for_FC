# Data Schema

> **Source**: `/home/lee/white_forest/whiteforest/backend/data_service/apt_postgresql_db/`
> 如果表结构有变更，以源码为准，更新此文档。

## 数据源

Livins AI 房源数据库。PostgreSQL + PostGIS，通过 data_service FastAPI 访问。

---

## 表结构

### buildings — 建筑信息

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigInteger PK | 建筑唯一标识 |
| address | String | 地址 |
| city | String | 城市 |
| state | String | 州 |
| borough | String | 区（Manhattan, Brooklyn, Queens, Bronx, Staten Island） |
| neighborhood | String | 社区 |
| zipcode | String | 邮编 |
| location | Geography(POINT) | PostGIS 坐标 |
| building_name | String | 建筑名称 |
| property_type | String | 物业类型 |
| built_in | Integer | 建造年份 |
| building_amenities | JSONB | 建筑设施 (key-value) |
| pet_policy | String | 宠物政策 |
| nearby_schools | JSONB | 附近学校 |
| rating | Float | 评分 |
| google_rating | Float | Google评分 |
| website | String | 官网 |
| phone | String | 电话 |
| email | String | 邮箱 |
| landlord_id | BigInteger | 房东ID |
| mobility_score | JSONB | 社区出行评分 |

### listings — 房源列表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigInteger PK | 房源唯一标识 |
| building_id | BigInteger FK | 关联建筑 |
| status | String | 状态：open / closed |
| unit_number | String | 房间号 |
| floor | Integer | 楼层 |
| price | Integer | 月租金($) |
| bedrooms | Integer | 卧室数（0=Studio） |
| bathrooms | Float | 卫生间数 |
| sqft | Float | 面积(平方英尺) |
| type | String | 租赁类型 |
| description | Text | 房源描述 |
| listed_at | Date | 上架日期 |
| available_from | Date | 可入住日期 |
| closed_at | Date | 下架日期 |
| days_on_market | Integer | 在架天数 |
| agent_name | String | 经纪人 |
| image_urls | JSONB | 图片URL列表 |
| unite_amenities | JSONB | 房间内设施 |
| **折扣字段** | | |
| min_lease_months | Float | 最短租期(月) |
| discount_free_rent_months | Float | 免租月数 |
| discount_free_rent_amount | Float | 免租金额($) |
| security_deposit_waived | Boolean | 押金减免 |
| application_fee_waived | Boolean | 申请费减免 |
| no_broker_fee | Boolean | 无中介费 |
| max_discount | Float | 最大折扣总额($) |
| discount_pct_off | Float | 折扣百分比 |
| discount_description | String | 折扣描述(LLM生成) |
| ranking_score | Float | 排名分数(内部) |
| low_income | Boolean | 低收入住房 |

### ml_listings — ML特征

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigInteger PK | |
| listing_id | BigInteger FK (unique) | 关联房源 (1:1) |
| has_floor_to_ceiling_windows | Boolean | 落地窗 |
| has_balcony | Boolean | 阳台 |
| has_hardwood_floors | Boolean | 硬木地板 |
| has_bathtub | Boolean | 浴缸 |
| overall_decoration_style | String | 装修风格 |
| overall_condition_level | Integer 1-5 | 房况评级 |
| aesthetic_score | Float 0-10 | 美学评分 |
| windows_direction | JSONB | 窗户朝向列表 |

### building_isochrones — 通勤范围

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigInteger PK | |
| building_id | BigInteger FK | 关联建筑 |
| transportation_mode | String | 出行方式：walking/transit/driving |
| duration_minutes | Integer | 时长：15/30/60 |
| polygon | Geography(MULTIPOLYGON) | 可达范围多边形 |

---

## 表关系

```
buildings ──1:N──► listings ──1:1──► ml_listings
    │
    └──1:N──► building_isochrones
```

---

## Data Service API

> Source: `/home/lee/white_forest/whiteforest/backend/data_service/data_api_service/apt_data_api_v2.py`

### 报表 Agent 使用的 Endpoints（Text-to-SQL）

报表 Agent 通过以下两个通用 endpoint 完成所有数据查询，不依赖业务专用 endpoint：

| Endpoint | Method | 请求 | 返回 | 说明 |
|----------|--------|------|------|------|
| `/query/execute` | POST | `{"sql": "SELECT ..."}` | `{"columns": [...], "rows": [...], "row_count": N}` | 执行只读 SQL（AST 校验 + 白名单表 + 超时 + 行数限制） |

**安全保障**（在 data_service API 层实现）：
- sqlglot AST 解析：只允许 SELECT，禁止 DROP/INSERT/UPDATE/DELETE/CREATE/ALTER
- 白名单表：只允许 buildings, listings, ml_listings, building_isochrones
- 只读数据库连接
- 查询超时限制
- 返回行数限制

### 现有业务 Endpoints（供前端使用，Agent 不直接调用）

| Endpoint | Method | 说明 |
|----------|--------|------|
| `/stats` | GET | 平台统计 |
| `/listings/` | GET | 房源列表（分页） |
| `/listings/{id}/details` | GET | 房源详情 |
| `/buildings/{id}/isochrones` | GET | 通勤范围 |
| `/top-ranked-listings` | GET | 推荐房源 |
| `/discount-listings` | GET | 折扣房源 |

### Agent 如何查询？（SQL 示例）

| 用户需求 | Agent 生成的 SQL |
|----------|-----------------|
| "曼哈顿一居室均价趋势" | `SELECT DATE_TRUNC('month', listed_at) AS month, AVG(price) FROM listings JOIN buildings ON ... WHERE borough='Manhattan' AND bedrooms=1 GROUP BY month` |
| "各区房价对比" | `SELECT borough, AVG(price), MIN(price), MAX(price), COUNT(*) FROM listings JOIN buildings ON ... GROUP BY borough` |
| "找Manhattan最便宜的5套" | `SELECT * FROM listings JOIN buildings ON ... WHERE borough='Manhattan' ORDER BY price LIMIT 5` |
| "装修评分和价格的关系" | `SELECT condition_level, AVG(aesthetic_score), AVG(price) FROM ml_listings JOIN listings ON ... GROUP BY condition_level` |
