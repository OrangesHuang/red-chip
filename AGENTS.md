# AGENTS.md — 红筹高股息因子分析（red-chip）

本项目以 Resonance（同频 ETF 监控）为框架蓝本，技术栈与分层约定保持一致。

## 项目定位

- 基于**红筹股**（注册境外/香港、香港上市、中资控股）做**个股级**高股息因子分析。
- 回答三个问题：值不值得买（六因子打分）、现在贵不贵（股息率锚定价格区间）、赔率如何（上行/下行）。

## 分层与依赖方向（严格单向，禁止跨层）

```
base/fetch/   → 领域 dividend/analysis/（纯函数无 I/O） →  dividend/service.py（编排，含 I/O）
base/store/   → 领域 dividend/api.py / api/data.py（请求解析与响应格式化）
base/scheduler/（定时任务，组合 service）
main.py 仅做 app 组装
```

- 页面私有逻辑进领域目录 `dividend/`，跨页共用下沉 `base/`。
- **股票池统一走 `base/pool.py`**（内置 config.STOCKS + 用户自定义 custom_stocks 表合并），
  禁止直接读 config.STOCKS；页面添加股票经 `add_stock()` 校验（5/6 位代码、市场推断、防重复），
  内置股票不可删，自定义删除时清理其全部数据。
- `base/fetch/` 只做请求与解析，失败一律返回空/None，**不抛异常**（优雅降级）。
- `dividend/analysis/` 全部纯函数（yield_series / factors / range / odds），可单测。
- SQL 全部参数化；表结构变更走 `database.py` 的 CREATE IF NOT EXISTS + `_migrate_*` 迁移。

## 数据源与口径（改动前必读）

| 数据 | 源 | 备注 |
|---|---|---|
| 日K（前复权） | 腾讯 `ifzq.gtimg.cn`（主）/ `web.ifzq.gtimg.cn`（备，双域名互备），A/H 通用（symbol=`hk00941`/`sh600941`/`sz000858`），新浪降级 | 市场由股票池 `market` 字段决定；区间拉取按自然日分块（单次上限约 640~700 根）；**回填 >600 根必须走日期区间路径**（无日期路径会被腾讯截断在 ~640 根）；腾讯整体不可用时 A 股降级新浪大 datalen（港股新浪仅 ~100 根不可降级） |
| 实时行情 | 腾讯 `qt.gtimg.cn/q={symbol}` | 港股成交量单位为股 |
| 分红历史 | 港股: `stock_hk_dividend_payout_em`（东财主源）+ `stock_hk_fhpx_detail_ths`（同花顺降级）；A股: `stock_fhps_detail_em`（东财结构化列） | 东财港股「特别分配」打 `special` 标记；A 股每股 = 每10股比例/10，人民币含税口径 |
| 个股资讯 | A股: akshare `stock_news_em`（东财，含来源/摘要）；港股: 腾讯 `proxy.finance.qq.com/ifzqgtimg/appstock/news/info/search?symbol={sym}&n={n}&type=1&page=0` | 资讯为瞬态数据**不入库**，内存 TTL 缓存 2 分钟（`base/fetch/news.py`）；A股东财失败自动降级腾讯 |

- **股息率 = 滚动 12 个月除净分红合计 ÷ 现价**（TTM）。窗口内可能落到 3 次派息（半年派息公司），属正常口径。
- **特别股息默认从 TTM/成长性剔除**（`EXCLUDE_SPECIAL_DIVIDENDS`），历史表仍展示并打标。
- 港股外币分红优先取方案文本「相当于港币X元」，否则按 `FX_RMB_HKD` / `FX_USD_HKD` 折算；A 股人民币无需折算。
- 财务类因子（派息率/负债率）数据源未接入，当前为 None → 权重自动归一化，**不要**把缺失当错误。

## 关键约定

- 代码格式：ruff（line-length=120）、mypy 见 `backend/`；新代码保持 `from __future__ import annotations`。
- 测试：`backend/tests/` pytest，核心纯函数必须有单测，**不触网**（LLM 用 monkeypatch 假实现）。
- 端口：后端 8092、前端 5190（勿与 Resonance 的 8001/5174 及其他项目冲突）。
- 数据库：**项目内 `data/red_chip.db`**（默认，`RED_CHIP_HOME` 可覆盖；勿改为 `~/.red-chip`，会与开发数据分裂）。
- 股票池编辑 `base/config.py` 的 `STOCKS` 即可，勿硬编码到页面/接口。
- 前端 A 股颜色习惯：红=涨/优，绿=跌/差。
- 前端改动后 `npm run build`（tsc）验证 + `npm run lint`；后端改动后跑 pytest。
- **Python 3.9 运行时**：`requirements.txt` 的 `eval_type_backport` 不可删——pydantic 模型里用了 PEP 604 的
  `str | None` 注解，缺它会在 3.9 导入时报错（`from __future__ import annotations` 只让源码可解析）。
- `./start.sh` 交互终端下会 `nohup` 自后台化（日志 `nohup.out`），且**每次启动先 kill 8092/5190 端口并清
  `__pycache__`**；停止用 `pkill -f 'uvicorn main:app.*--port 8092'`，前台运行加 `--foreground`。

## LLM 分析（AI 深度分析）

- 位置：`base/llm/`（client 客户端 + agent ReAct 循环 + jobs 任务表）、`api/analysis.py`、前端 `components/analysis/`。
- **ReAct 协议**：模型每步输出 JSON，`{"tool": "...", "args": {...}}` 或 `{"final": "报告"}`；
  用 deepseek-chat 的 `response_format=json_object` 保证解析可靠（`parse_llm_json` 容忍代码围栏）；
  **空响应/解析失败自动重试提示**（不静默带病继续），兜底仍无效则报 LLMError。
- **防错标的(重要)**：`get_stock_data`/`get_stock_news` 漏传 code 时由 agent 循环**注入本次分析
  目标代码**(曾因回退 DEFAULT_STOCK_CODE=00941 导致腾讯控股会话弹出中国移动数据);
  多轮追问消息自动前置「【本次分析标的: code 名称(市场)】」头。
- **工具注册表** `agent._TOOLS`：get_stock_data / get_stock_news / get_pool / bash（30s 超时+截断）。
  新增工具：写函数 + 注册 + 在 SYSTEM_PROMPT 里加描述。
- 数据上下文：`dividend/service.build_llm_context(code)`（紧凑版，~1k token，禁传全量 K 线）。
- API Key 存 settings 表（本地明文，响应掩码）；未配置时 LLMError → 任务 error 状态，前端提示配置。
- **多轮会话**：`analysis_session` 表（消息 JSON）；`run_analysis(code, history=...)` 携带前序
  问答对；**历史只保留「用户提问 + AI 报告」**（工具内部细节不保留 → 前缀紧凑、缓存友好）。
  DeepSeek 磁盘缓存自动启用，`chat_completion_rich` 返回 `cache_hit/miss_tokens`，每轮以
  `usage` 步骤展示，消息级 usage 持久化在会话中。
- 会话 API：`/api/analysis/sessions`（创建/列表/详情/发消息）；发消息 = 追加 user 消息 +
  后台启动新回合，轮询 `/api/analysis/jobs/{id}` 同单轮。
- 分析任务为内存态（进度实时可见）；**完成后自动持久化到 `analysis_report` 表**
  （`base/store/analysis_repo.py`，完成/失败均入库，含全文 + 步骤 JSON），重启不丢；
  历史报告接口 `/api/analysis/reports`。
- 测试：`tests/test_agent.py` 用 monkeypatch 的假 LLM 验证循环/解析/兜底（不触网）。

## 常用命令

```bash
./start.sh                                            # 一键启动前后端（交互终端自动后台化）
./start.sh --foreground                               # 前台启动（日志直出）
cd backend && ../.venv/bin/python -m pytest tests -q  # 后端全量单测
cd backend && ../.venv/bin/python -m pytest tests/test_factors.py::test_name -q  # 单测/单用例
cd frontend && npm run build                          # 前端 tsc + 构建
cd frontend && npm run lint                           # 前端 eslint
.venv/bin/python scripts/seed_daily.py                # CLI 全池回填（默认 1250 交易日）
.venv/bin/python scripts/seed_daily.py 600 00941      # 深度 + 单只
```
