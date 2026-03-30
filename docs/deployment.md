# Deployment

## Prerequisites

- Python 3.12+
- Anthropic API Key 或 OpenAI API Key
- 访问 Livins AI data_service（生产环境）

## Installation

```bash
cd /home/lee/livins_report_agent
pip install -e ".[dev]"
```

## Configuration

```bash
cp .env.example .env
# 编辑 .env 设置 API Key 和其他配置
```

### Environment Variables

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_MODEL` | `anthropic:claude-haiku-4-5-20251001` | LLM 模型 |
| `ANTHROPIC_API_KEY` | - | Anthropic API Key |
| `USE_MOCK_CLIENT` | `true` | 是否使用 Mock 数据 |
| `DATA_SERVICE_URL` | `http://localhost:8002` | data_service API 地址 |
| `MAX_AGENT_STEPS` | `15` | Agent 最大推理步数 |
| `API_HOST` | `0.0.0.0` | 服务监听地址 |
| `API_PORT` | `8000` | 服务监听端口 |
| `REPORT_OUTPUT_DIR` | `./reports` | 报告文件输出目录（后续升级用，Demo 阶段文件通过 Files API 流式转发） |

## Running

### Development (Mock Data)

```bash
USE_MOCK_CLIENT=true uvicorn livins_report_agent.main:app --reload
```

### Production

```bash
USE_MOCK_CLIENT=false \
DATA_SERVICE_URL=http://data-service:8002 \
ANTHROPIC_API_KEY=sk-... \
uvicorn livins_report_agent.main:app --host 0.0.0.0 --port 8000
```

## Testing

```bash
# Full suite
pytest

# Specific test
pytest tests/test_tools/test_query.py -v

# With coverage
pytest --cov=livins_report_agent
```

## Verification

```bash
# Health check
curl http://localhost:8000/health

# Chat test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "分析曼哈顿一居室的平均租金"}]}'
```
