# 红筹高股息因子分析（Red-Chip High-Dividend Factor Analysis）

> 基于**红筹股**的高股息因子分析系统：选出优质的高股息股票，判断其**价格区间**与**赔率**。
> 本次为**个股级**分析（区别于指数/ETF 组合）。

## 一、核心思想

红筹股（注册境外/香港、香港上市、中资控股）是港股高股息的主战场：电信（中国移动/联通）、
能源（中海油）、公用事业（华润电力/燃气）、银行（中银香港）等常年保持 4%~8% 的分红回报。
池子同时纳入 A 股高股息主线（银行/煤炭/公用/白酒），A/H 同标的可对照（如中国移动 H 股
股息率显著高于 A 股，反映 A/H 溢价）。

对每只股票，系统回答三个问题：

1. **值不值得买** —— 高股息六因子打分（0~100，分优质/良好/一般/回避）
2. **现在贵不贵** —— 股息率锚定的价格区间（深度低估/低估/合理/高估/深度高估）
3. **赔率如何** —— 上行空间 ÷ 下行空间（股息率历史分位锚定目标价与悲观支撑价）

### 六因子模型

| 因子 | 权重 | 说明 |
|---|---|---|
| 股息率(TTM) | 35% | 近 12 个月除净分红合计 ÷ 现价，越高越好 |
| 分红持续性 | 20% | 近 5 个日历年内有分红的年数 |
| 分红成长性 | 15% | 最新已完成财政年度 vs 3 年前每股股息 CAGR |
| 派息率 | 15% | 健康区间 30~70%（数据源未接入时自动降级，权重归一化） |
| 负债率 | 10% | 越低越稳健（同上，可降级） |
| 低波动 | 5% | 年化波动率越低越稳 |

### 价格区间与赔率（股息率锚定）

高股息股用「股息率」定价：股息率越高 = 价格越便宜。以近 5 年逐日 TTM 股息率
序列的分位为基准：

```
股息率 ≥ P75 → 低估区     ≥ P90 → 深度低估
股息率 ≤ P25 → 高估区     ≤ P10 → 深度高估

中枢价     = 每股股息 ÷ P50 股息率        （估值回到历史中枢的目标价）
乐观价     = 每股股息 ÷ P25 股息率        （估值回到较贵端的上限参考）
悲观支撑价 = 每股股息 ÷ P95 股息率        （估值走到最便宜端的支撑价）

上行空间 = 中枢价/现价 - 1
下行空间 = 1 - 悲观支撑价/现价（现价已低于悲观价时归零）
赔率     = 上行空间 ÷ 下行空间（≥3 高赔率 / ≥1.5 中等 / 其余低赔率）
```

### 数据口径约定

- **股息率 = 滚动 12 个月除净分红合计 ÷ 现价**（TTM 口径）。半年派息公司窗口内
  可能落到 3 次派息，与券商「年度股息率」口径有差异，区间/赔率判定在同一口径下自洽。
- **A 股分红为含税口径**（每10股派X元(含税)，每股=X/10 元人民币；红利税按持股时长
  由券商代扣，个人实际到手低于含税金额，见 `A_SHARE_TAX_POLICY`）；港股分红按
  「相当于港币」金额或折算率换算为港币等值。
- **特别股息默认剔除**（东财「特别分配」，如昆仑能源出售资产后的一次性派息），
  避免污染股息率锚点；分红历史表中仍展示并打「特别」标记。
- 外币分红按方案文本给出的「相当于港币」金额优先，否则按 config 折算率近似
  （人民币 ×1.10、美元 ×7.80，可调）。

## 二、技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.9 · FastAPI · uvicorn · APScheduler |
| 数据源 | 腾讯行情（港股日K/实时）· akshare 东财港股分红（同花顺降级） |
| 存储 | SQLite（WAL 模式，参数化查询） |
| 前端 | React 18 · TypeScript(strict) · Vite · React Query v5 · ECharts · Tailwind |

## 三、目录结构

```
red-chip/
├── backend/
│   ├── main.py            # FastAPI 组装入口（仅组装 + 启动调度器）
│   ├── base/
│   │   ├── config.py      # 股票池/因子权重/区间阈值/限流，全部可调常量
│   │   ├── fetch/         # kline(腾讯港股+新浪降级) / realtime / dividend / calendar
│   │   ├── analysis/      # position(分位数/价格位置/波动率) 纯函数
│   │   ├── store/         # database + stock/dividend/factor/settings repo
│   │   ├── scheduler/     # APScheduler 定时任务（工作日 16:35 自动刷新）
│   │   └── api/           # static（生产静态托管）
│   ├── dividend/          # 高股息分析领域（个股）
│   │   ├── analysis/      # yield_series / factors / range / odds —— 全部纯函数
│   │   ├── service.py     # 编排：拉取→入库→快照
│   │   └── api.py         # /api/dividend/*（pool / stock / refresh）
│   ├── api/data.py        # /api/data/status、/api/data/rebuild
│   └── tests/             # pytest（因子/区间/赔率/股息率序列，21 用例）
├── frontend/
│   └── src/
│       ├── pages/         # Dashboard(股票池) / StockDetail(个股) / DataManage(数据)
│       ├── components/    # common/Layout、kline/KlineChart、YieldZoneChart
│       ├── api/           # client.ts + types.ts
│       └── hooks/         # useStocks.ts（React Query）
├── scripts/seed_daily.py  # CLI 回填（薄壳）
└── start.sh               # 一键启动
```

## 四、快速开始

### 一键启动（推荐）
```bash
./start.sh
```
自动创建虚拟环境、安装前后端依赖（仅缺失时），同时启动后端（:8092）与前端（:5190）。

### 手动方式
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install
# 后端 :8092
cd backend && python3 -m uvicorn main:app --port 8092
# 前端 :5190（已配置 /api 代理到 :8092）
cd frontend && npm run dev
```

打开 http://localhost:5190 ，进入「数据管理」页点击**全量重建**
（默认回填 1250 个交易日 ≈ 5 年，约 1~2 分钟），即可在「股票池」看到全部分析结果。
个股详情页底部提供**个股资讯**（A 股来源东财新闻，港股来源腾讯新闻，点击标题打开原文）。

### CLI 回填（无需 Web）
```bash
.venv/bin/python scripts/seed_daily.py            # 全池，默认 1250 交易日
.venv/bin/python scripts/seed_daily.py 600        # 指定深度
.venv/bin/python scripts/seed_daily.py 600 00941  # 单只股票
```

> 数据库默认位于**项目内 `data/red_chip.db`**（已在 .gitignore），可用环境变量 `RED_CHIP_HOME` 覆盖。

## 四·五、AI 深度分析（DeepSeek ReAct Agent）

个股详情页底部「AI 深度分析」是**多轮会话**：第一轮自动发起全面分析（Agent 多轮调用
工具：个股数据 / 资讯 / 全池对照 / bash），之后你可以**持续追问、补充自己的分析思路**
（如"重点评估分红可持续性""与神华对比"），AI 基于完整会话历史继续深化分析。
会话与全部消息持久化到 SQLite，可切换回看任意历史会话。

**执行过程实时呈现**：进度条 + 计时器，每步展示模型决策（原始 JSON，可展开）、工具调用
与返回摘要、单步耗时；每轮还显示 **DeepSeek 磁盘缓存命中统计**（输入 tokens 中缓存命中/
未命中的占比，命中部分费用约 1/10）。

**缓存机制**：DeepSeek 对 deepseek-chat 自动启用上下文磁盘缓存。系统提示词恒定 +
历史只追加「提问/报告」问答对（工具内部细节不进长期历史）→ 前缀稳定可命中缓存；
实测多轮会话缓存命中率约 60%~99%。

- 配置：数据管理 → AI 分析设置（API Key 仅存本地 SQLite；模型/端点可改，默认 deepseek-chat）
- 工具注册表：`backend/base/llm/agent.py` 的 `_TOOLS`，加工具 = 加一个函数 + 一行注册
- 任务机制：后台线程执行，前端 1.5s 轮询进度；**报告完成后持久化到 SQLite
  `analysis_report` 表（重启不丢）**，个股页「历史报告」可回看任意一次分析全文与步骤日志
- 免责：报告由 AI 基于历史数据生成，不构成投资建议

## 五、接口一览

| 接口 | 说明 |
|---|---|
| `GET /api/dividend/pool` | 股票池：因子总分降序 + 实时行情叠加（含 custom 标记） |
| `GET /api/dividend/pool/custom` | 自定义股票列表 |
| `POST /api/dividend/pool` | 添加股票（自动识别市场/补全名称，并立即拉取数据） |
| `DELETE /api/dividend/pool/{code}` | 移除自定义股票并清理数据 |
| `GET /api/dividend/stock/{code}?days=` | 个股详情：K线/分红/因子明细/区间/赔率/股息率曲线 |
| `GET /api/dividend/stock/{code}/news?limit=` | 个股资讯（A股东财/港股腾讯新闻，内存缓存 2 分钟） |
| `GET/PUT /api/analysis/settings` | AI 设置查询/保存（API Key 掩码展示） |
| `POST /api/analysis/test` | LLM 连通性测试 |
| `POST /api/analysis/sessions` | 创建多轮分析会话 |
| `GET /api/analysis/sessions?code=` | 会话列表 |
| `GET /api/analysis/sessions/{id}` | 会话详情（完整消息历史 + 每轮缓存统计） |
| `POST /api/analysis/sessions/{id}/messages` | 发送提问（含补充提示词）→ 启动分析回合 |
| `POST /api/analysis/stock/{code}` | 一次性分析任务（旧接口） → `{job_id}` |
| `GET /api/analysis/jobs/{job_id}` | 任务进度轮询（步骤日志 + 最终报告） |
| `GET /api/analysis/reports?code=` | 历史分析报告列表（摘要，按时间倒序） |
| `GET /api/analysis/reports/{job_id}` | 历史报告全文 + 步骤日志 |
| `POST /api/dividend/stock/{code}/refresh` | 手动刷新单只（120s 限流） |
| `GET /api/data/status` | 数据覆盖状态 |
| `POST /api/data/rebuild?days=` | 一键重建全池 |
| `GET /api/health` | 健康检查 |

## 六、股票池（红筹 12 只 + A 股高股息 18 只，可编辑 config 增删）

**红筹股（H）**：00941 中国移动 · 00762 中国联通 · 00883 中国海洋石油 · 00836 华润电力 ·
01193 华润燃气 · 00135 昆仑能源 · 00267 中信股份 · 02388 中银香港 · 00688 中国海外发展 ·
01109 华润置地 · 00992 联想集团 · 01093 石药集团

> 池子 = 内置精选（config.STOCKS，约 40 只）+ 用户自定义（页面「数据管理 → 股票池管理」添加，
> 存于 SQLite custom_stocks 表）。券商等低股息行业也纳入若干龙头作对照
> （如中信证券/华泰证券股息率仅 2~3%，分数自然垫底）。

### 页面自助添加/删除股票
- 打开「数据管理 → 股票池管理」：输入 5 位港股或 6 位 A 股代码即可添加（市场自动识别，
  名称自动从实时行情补全），添加后自动拉取约 5 年 K 线 + 分红并计算因子快照。
- 自定义股票可随时移除（同时清理其数据）；内置股票不可在页面删除（编辑 config.STOCKS 调整）。
- 定时任务/一键重建自动包含自定义股票。

**A 股高股息（A）**：600941 中国移动 · 601088 中国神华 · 601857 中国石油 · 600028 中国石化 ·
600900 长江电力 · 601398 工商银行 · 601939 建设银行 · 601288 农业银行 · 601328 交通银行 ·
601988 中国银行 · 601658 邮储银行 · 600036 招商银行 · 601166 兴业银行 · 601318 中国平安 ·
601601 中国太保 · 600030 中信证券 · 601688 华泰证券 · 601225 陕西煤业 · 601006 大秦铁路 ·
601668 中国建筑 · 600019 宝钢股份 · 600585 海螺水泥 · 600350 山东高速 · 600519 贵州茅台 ·
000858 五粮液 · 000651 格力电器 · 000333 美的集团 · 600887 伊利股份 · 000895 双汇发展

## 七、后续路线（TODO）

- [ ] 接入 A/H 财务数据源（akshare 东财财务指标），激活派息率/负债率两个因子
- [ ] 港股交易日历接入（当前用自然日近似分块拉取）
- [ ] A 股红利税口径可选（net 模式按持股时长折算实际到手股息）
- [ ] 赔率下行锚点增强：现价创 5 年新低（股息率超历史区间）时给出替代支撑参考
- [ ] 盘中实时快照入库与轮询
