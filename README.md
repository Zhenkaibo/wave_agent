# Wave Agent：波浪理论 + 信息层的分析工具

用代码做确定性的部分（找转折点、检查波浪铁律、算斐波那契目标、比较 MACD/RSI 动能），
用 Claude Code 做信息层（新闻、宏观日程、财报）和综合判断，并把每次判断记进 `journal/` 以便复盘。

> 技术分析框架，不构成投资建议。波浪计数有主观性，本工具只负责列出可能性和量化价位。

---

## 一、第一次使用（任何一台电脑）

### 1. 安装 Claude Code
- macOS / Linux：在终端运行 `curl -fsSL https://claude.ai/install.sh | bash`
- Windows：在 PowerShell 运行 `irm https://claude.ai/install.ps1 | iex`（推荐同时安装 Git for Windows）
- 安装后新开一个终端，运行 `claude --version` 确认。

### 2. 安装 Python 依赖（需要 Python 3.9+）
在项目文件夹里运行：
```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
```

### 3. 打开项目
```bash
cd 项目所在路径/wave-agent
claude
```
第一次会要求登录（用你的 Claude 账号）。Claude Code 会自动读取 `CLAUDE.md`，知道这个项目的规则和用法。

### 4. 试一下
在 Claude Code 里输入：
```
/wave-analyze WTI 74,88.5,80.5,106,89.5
```
或者直接说“帮我分析一下黄金现在的波浪”。

也可以不经过 Claude，直接跑脚本：
```bash
python -m wavekit.analyze --csv data/sample/wti_daily.csv --pivots 74,88.5,80.5,106,89.5 --symbol WTI
python -m wavekit.analyze --csv data/sample/wti_daily.csv --auto --threshold 8 --symbol WTI
python -m pytest -q
```
报告和图表会保存在 `reports/`。

---

## 二、项目结构

```
wave-agent/
├── CLAUDE.md                  ← Claude Code 每次都会读的项目说明（规则、命令、陷阱）
├── .claude/
│   ├── settings.json          ← 项目权限（允许跑分析脚本、禁止读 .env）
│   └── skills/
│       ├── wave-analyze/      ← /wave-analyze：波浪 + 新闻综合分析
│       └── wave-journal/      ← /wave-journal：记录与复盘
├── docs/wave-rules.md         ← 波浪规则、经验比例、本次原油案例
├── src/wavekit/               ← Python 分析代码
│   ├── zigzag.py              转折点
│   ├── rules.py               铁律与经验打分
│   ├── fib.py                 斐波那契目标
│   ├── indicators.py          RSI / MACD
│   └── analyze.py             命令行入口与报告
├── data/sample/wti_daily.csv  ← WTI 日线样例
├── journal/                   ← 每次判断的记录（只追加，不改写）
├── reports/                   ← 生成的报告和图（不会被分享）
└── tests/                     ← 单元测试
```

## 三、放到移动硬盘 / 换电脑

可以直接把整个 `wave-agent` 文件夹拷到移动硬盘，在另一台电脑上打开。需要注意：

| 内容 | 会跟着文件夹走吗 | 说明 |
|---|---|---|
| 代码、CLAUDE.md、skills、journal、数据 | 会 | 这些就是项目本身 |
| `.venv`（Python 虚拟环境） | 不建议带 | 和电脑系统绑定，换电脑后删掉重新执行第一步的第2步 |
| Claude Code 登录状态 | 不会 | 在新电脑上安装 Claude Code 后重新登录一次 |
| 和 Claude 的对话记录 | 不会 | 保存在每台电脑自己的 `~/.claude` 里。重要结论要写进 `CLAUDE.md`、`docs/` 或 `journal/`，才能在别的电脑上延续 |
| `.env`（以后放 API key） | 会，但要小心 | 不要把它分享给别人 |

## 四、分享给别人

推荐用 Git + GitHub（也方便你自己在多台电脑之间同步）：
```bash
git init
git add .
git commit -m "init wave-agent"
# 在 GitHub 新建一个私有仓库后：
git remote add origin <你的仓库地址>
git push -u origin main
```
`.gitignore` 已经排除了 `.env`、`.venv`、`reports/` 和个人设置（`.claude/settings.local.json`、`CLAUDE.local.md`），
所以别人拿到的是干净的项目。对方按“第一次使用”的步骤操作即可。

如果不用 Git，直接压缩文件夹发送也可以，但发之前删掉 `.env` 和 `.venv`。

### 个人设置怎么放
- 只想自己生效的 Claude 指令（比如你的持仓、风险偏好）：写在项目根目录的 `CLAUDE.local.md`。
- 只想自己生效的权限设置：`.claude/settings.local.json`。
这两个文件不会被提交或分享。

## 五、下一步可以做的
- 接入行情数据（cTrader 导出 CSV，或用行情 API 自动下载）。
- 多级别数浪（日线 + 4 小时）。
- 调整浪形态（锯齿、平台、三角形）识别。
- 把 `journal/` 的判断自动汇总成命中率统计。
- 移植成 cTrader 指标（C#），在图上直接标注目标位和作废位。

## 已知局限
- 自动数浪对阈值敏感：同一份数据，阈值不同结果不同。建议先用 `--pivots` 验证自己的数法。
- 样例数据缺少 2026-07-30 至 08-11，且是连续合约，和你自己软件里的合约价格可能有出入。
- 大模型读新闻的效果无法用历史回测证明（模型可能“记得”历史），只能靠 `journal/` 往后记录来检验。
