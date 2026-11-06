# Satellite Resource Catalog v0.2

基于本地 CSV 的 Earth Observation 卫星资源查询网页，使用 Python 3.11、Streamlit 和 pandas。
当前包含 4 条 SAR 资源记录；一条记录可能代表任务、星座或资源系列，不等同于一颗卫星。

## 安装与运行

在仓库根目录执行（需要 Python 3.11）：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Windows PowerShell 可使用 `py -3.11 -m venv .venv`，然后执行
`.venv\Scripts\Activate.ps1`；后续命令相同。浏览器访问 <http://localhost:8501>。
数据文件通过 `catalog.py` 的位置定位，不依赖当前工作目录。应用只读本地 CSV，安装依赖后不需要外部卫星服务。

## 使用规则

- 默认按 CSV 原始顺序显示全部记录。
- 搜索覆盖 `satellite`、`operator`、`sensor_type`、`primary_application`，不区分大小写，按普通子串匹配（`regex=False`），不解释正则表达式。
- `operator` 和 `sensor_type` 支持多选。同一字段内为 OR，不同字段与搜索条件之间为 AND；未选择表示不限。
- 筛选选项来自完整数据的非空值，不随搜索结果缩减、不写死；选项保留首次出现顺序。
- 点击“重置”同时清空搜索和两个筛选条件。
- 空字段、仅含空白的字段在界面中显示“未提供”，搜索时作为空字符串；占位文字不参与查询。不会推断或补造卫星属性。
- 无匹配时显示空表格和提示；文件缺失、空文件、缺少必需列和 CSV 解析异常分别显示错误消息。

## 数据与校验

数据源：`data/sar_satellites.csv`，UTF-8（兼容 UTF-8 BOM）。必需字段：

| 字段 | 含义 |
| --- | --- |
| `satellite` | 资源、任务或星座名称 |
| `operator` | 运营机构 |
| `sensor_type` | 传感器类型 |
| `primary_application` | 原始应用描述，自由文本 |

原始 CSV 保持不变。读取时忽略空白行；短行末尾缺失字段按空字符串处理；超出表头列数、重复列名、引号未闭合或非 UTF-8 编码报错。
额外列不用于当前页面；缺少必需列则停止展示。只有表头、没有记录也会报空目录错误。
非空原始文本保留不变，字面值 `NA`、`null` 不自动转为缺失值。无缓存，每次 Streamlit 重运行重新读取文件。

## 目录结构

```text
app.py                      # Streamlit UI 和重置操作
catalog.py                  # 读取边界、纯解析/校验/查询/展示函数，不依赖 Streamlit
data/sar_satellites.csv      # 只读原始业务数据
requirements.txt            # 固定版本的运行依赖
requirements-dev.txt        # 测试依赖
tests/test_catalog.py       # 数据与查询单元测试
tests/test_app.py           # Streamlit AppTest 交互测试
```

## 测试与验收

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

测试使用临时 CSV 和内存数据覆盖异常场景，不修改业务 CSV。AppTest 无需启动浏览器。
覆盖原始 4 条记录、四字段大小写搜索、普通特殊字符、多选 OR、跨条件 AND、原始顺序、动态选项、空结果、空字段、空白尾行、缺列、缺文件、空文件、解析及编码异常、界面错误提示和重置。

手工验收：

1. 初次打开显示“匹配 4 / 共 4 条资源记录”。
2. 搜索 `sentinel` 仅返回 Sentinel-1；`DISASTER` 返回 RADARSAT Constellation Mission 和 ICEYE constellation。
3. 搜索 `disaster` 并选择 Capella Space，显示空结果提示；点击重置恢复 4 条。
4. 搜索 `[` 不出现 traceback；operator 的选项仍来自完整数据。

CSV 完整性检查（在仓库根目录）：

```bash
python -c "import hashlib; from pathlib import Path; print(hashlib.sha256(Path('data/sar_satellites.csv').read_bytes()).hexdigest())"
git hash-object data/sar_satellites.csv
git diff HEAD -- data/sar_satellites.csv
```

原始 SHA-256：`f337c0aa8d8d67d9342cc5a3135f5aae2ba5cea31c836d94e00a29d5df5984f5`。
原始 Git blob SHA：`523c4d1217a94219cc41a92f45117833708462ee`。最后一条命令应无输出。
完整性测试也固定验证当前数据基线；未来有意更新数据时，需要另行审查并同步测试基线。

## 范围与限制

仅实现静态目录浏览、搜索、筛选和重置。不包含数据库、Docker、登录与权限、外部 API、地图、轨道预测或资源调度。
当前仅 4 条 SAR 数据，无轨道、分辨率、重访周期、覆盖范围、价格、状态或数据来源日期，不能据此筛选或保证实时有效性。
`primary_application` 按原始自由文本搜索，不自动拆分分类。默认以本地单机运行验收；不包含托管部署配置。
