# 南岸剧场 · 场次上座与引导员排班

以连续验票日历预估下一周上座，再把预测转换成开场前点名。

模拟客户：南岸小剧场，160席、16人场务组，主演剧目《潮汐独白》。过去票务用Excel交验票数，场务按经验排人，周末热场与工作日混估；预测可能超过座位；缺班和点名延误没有后端约束。本项目承接票务验票，替代上座预估和排班核对，交付给值班经理确认的场务点名单。

## 业务模块

- 演出日历：Production剧目与Performance场次关联，每剧目每天一场；剧目有座位容量与演出时长。
- 验票历史：按日补录/修订真实范围的观众人数，不能超过座位；日期缺口阻止预测。
- 上座预测：Python worker执行Holt-Winters周季节预测；更早49天训练、最近7天回测，再用56天预测下一周；页面展示回测误差、原始需求、座位封顶值和所需引导员。
- 实名到岗：已确认点名分配StaffMember到CrewAssignment，保留姓名编号快照；跨剧目占用时段重叠、停用或超个人每日上限拒配；现场到岗限点名时刻前后15分钟，登记后不可重复。
- 散场交接：实名签到人数达到已确认配置才能保存ShowDebrief；实到人数不得超座位；散场>15分钟或上座偏差>30%须至少8字原因；领班可修订草稿，经理归档后冻结。
- 场务点名：每40位预计观众至少1名引导员，向上取整，最少1名；点名须在开场前30分钟至6小时内；经理确认时检查人手与有效预测。成功确认关联场次状态。

修改验票或剧目资料会使未确认预测及草案失效；已有确认点名后，上游输入和预测冻结，避免已确认的人手依据被改写。确认点名不能重复确认或改班。

## 启动与演示账号

```sh
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
docker compose exec -T backend python -m scripts.seed_demo
```

[工作台](http://localhost:18224)；[API文档](http://localhost:19224/docs)；PostgreSQL端口17724。

|账号|口令|角色|任务|
|---|---|---|---|
|admin@nanan.demo|Curtain2026!|admin 值班经理|修订剧目、人员可用性、全部录入、确认点名及交接归档|
|steward@nanan.demo|Curtain2026!|steward 场务领班|登记场次、校正验票、预测、编制点名、实名排班/到岗、散场交接草稿；不能签署|
|viewer@nanan.demo|Curtain2026!|viewer 观察员|九页只读|

## 一天的工作剧本

1. 08:30 经理查看NA-TIDE《潮汐独白》，160席、95分钟，19:30开场。
2. 09:00 票务核对2026-09-22至11-16共56天验票，0观众也应记录，不能漏日。
3. 09:30 在验票历史校正人数；新输入会使旧预测和待确认点名失效。
4. 10:00 领班预测11-17至11-23上座，检查最近7日回测误差与周末需求。
5. 10:30 为11-17场次安排18:45点名；预计人数每40人需要1名引导员。
6. 11:00 演练1名引导员的不足草案，经理确认被拒，补足4名后再确认。
7. 14:00 经理确认点名，Performance由forecasted变成crew_confirmed，CrewCall变confirmed。
8. 16:00 观察员查看已确认点名；历史输入已冻结。切到“排练厅缺口示例”演练缺日拒绝。

## 算法与可复现口径

输入是至少28天连续逐日验票序列。没有随机拆分：最后7天只做验证，前面的记录拟合statsmodels ExponentialSmoothing(trend=add,seasonal=add,seasonal_periods=7)；MAE=mean(abs(actual-predicted))。随后完整历史重拟合预测未来7天。原始需求=max(0,predicted)；排班人数基数=min(seats,ceil(raw))；所需引导员=max(1,ceil(base/40))。无随机拟合步骤，seed仅用于生成可复现模拟历史。参考数据是业务模拟，不代表真实剧院。

结果写入Production.forecast_evidence、Performance.forecast/raw_forecast与backend/worker共享产物卷。没有前端假预测。缺日、少于28天或已确认点名均阻止建模。

## 工程与本地开发

|层|实现|
|---|---|
|前端|原生HTML/CSS/JS ES modules、Nginx1.27|
|后端|Python3.12 FastAPI、SQLAlchemy、JWT|
|预测|statsmodels0.14.4、Redis worker|
|数据库|PostgreSQL16、Redis7 AOF|

五服务frontend/backend/worker/db/redis均有健康检查；worker写心跳；db/redis健康后启动应用，frontend依赖backend健康。Nginx `/api/` 去除前缀代理。命名卷保存db、redis、共享产物。`.env.example`提供端口、短名、JWT_SECRET、SEED_DEMO与显式可配10.221.25.0/24子网（本机默认地址池不足时使用）。

`backend/src/models.py`三个领域模型和User/Audit；`schemas.py`输入校验；`services.py`日历连续性、失效链、点名条件；`forecast.py`时序拟合；`worker.py`队列；`main.py`路由；`auth.py`JWT与PBKDF2；`middlewares.py`请求ID/限流；`scripts/seed_demo.py`自然键只增不覆盖。

前端`src/pages/calendar.js`节目日历、`history.js`验票、`forecast.js`预测、`crew.js`点名；`api.js`客户端、`store.js`状态、`components/shared.js`状态/容量条/日期块跨页复用、`utils/format.js`转义/日期/表单工具。

角色与场次/点名状态枚举在`backend/src/constants.py`和`frontend/src/constants.js`；所有权限以服务端为准。完整性错误统一转409，错误态可修正重试。

本地设置DATABASE_URL/REDIS_URL，backend目录安装requirements后运行`uvicorn src.main:app --reload`，另开`python -m src.worker`；前端建议使用Compose Nginx代理。停止保留数据`docker compose down`，验收清理`down -v --remove-orphans`。

已知范围：每剧目每日一场，人员占用会跨剧目检查；未接短信、门禁或考勤硬件。时间为本地Asia/Shanghai。已确认后输入冻结，小型版本没有取消确认/滚动下一周结转。worker故障后的可靠重投尚未实现。外部Google字体离线回退。运行证据位于`../../test-artifacts/gb-1025/`。

## 实名到岗与散场交接扩展

`staff_models.py` 的 StaffMember/CrewAssignment 记录在岗状态、每日场数和每场实名到岗；`staff_service.py` 以人员锁串行核对冲突，值班占用为点名时刻至开场＋演出时长＋30分钟，端点相接可连续值班。每日场数按点名日期统计。每份已确认点名单最多分配其配置人数，不以填报人数替代实名签到。

到岗采用领班登记现场发生的 `observed_at`（剧场本地时间，不附时区），必须在点名±15分钟窗口内；服务器另存 `recorded_at` 和 `recorded_by`，便于历史补录追溯。不是门禁自动签到，不以浏览器当前时间冒充现场时间。

`debrief_models.py` 的 ShowDebrief 保存实际人数、散场耗时、原因以及原预测、配置和实名到岗快照；`debrief_service.py` 校验容量、签到足额、延误与偏差。偏差=abs(实际－预测)/max(预测,1)×100%。保存草稿后班表冻结；经理归档后交接不可修改。实际人数保存在独立演后表，不覆盖已冻结的Performance预测。新增请求在 `frontdesk_schemas.py`，独立路由与权限在 `frontdesk_routes.py`，两页面为 `pages/staff.js` 和 `pages/debrief.js`。

|接口|权限|
|---|---|
|GET /staff、/crew-assignments、/show-debriefs|三角色只读|
|POST /staff、PUT /staff/{id}|admin维护人员可用性；编号不可改|
|POST /crew-assignments、/{id}/check-in|admin/steward实名排班与登记到岗|
|POST /show-debriefs、PUT /show-debriefs/{id}|admin/steward交接草稿与修订|
|POST /show-debriefs/{id}/archive|仅admin归档|

seed另有16名场务、1名停用示例，以及“交接演练·夜场”11-17/18与“交接演练·午场”11-17的已确认点名（各2人、预期80人）。这些是明确标识的运营交接演练快照，不作为Holt-Winters训练/指标；原NA-TIDE的56天历史与预测流程保持独立。自然键只插缺失数据，重复seed不覆盖人员姓名、签到和归档记录。三张新增表采用create_all建立，原有表没有新增列或历史回填。

新增交接状态在 `backend/src/constants.py` 和 `frontend/src/constants.js` 定义。当前没有请假撤岗、主管追加人手、取消归档或与真实票务对账；原人数配置不足的场次必须先在点名确认前修正。验收证据在 `test-artifacts/gb-1025/expansion/`。

## 入口、事件与失物（第三轮扩展）

7. 入口分区与岗位覆盖：EntranceZone绑定Production，保存容量、启用状态和最低值守人数，经理配置的总容量不能超过seats。ZonePost只接本场已签到CrewAssignment，一人本场一岗，跨剧目和重复安排拒绝。新的散场交接须先配置启用区，且逐区足额；旧archived记录保留。保存交接后本场岗位冻结，有待归档交接的剧目不能追加分区。
8. 现场事件与升级：HouseIncident关联同场同剧目入口，normal/high风险，open→经理分派同场已到岗人员assigned→场务登记处置resolved→经理复核closed。任意高风险未closed都阻止新交接归档，包括已处置待经理复核；归档后不再补报该场现场事件。
9. 失物保管与认领：LostItem保存场次、唯一编号、保管位置和场务识别特征。ItemClaim保存姓名和特征凭据；经理核对匹配后同时将申请和物品变handed_over。凭据不匹配拒交，可修订原申请重试；已交付不可修改、再认领或重复领取。物品锁和数据库部分唯一索引保证一件物品只有一笔成功交付。

|接口|权限|
|---|---|
|GET /entrance-zones、/zone-posts、/house-incidents、/lost-items、/item-claims|三角色读取；viewer看不到失物保管识别特征|
|POST /entrance-zones|admin配置入口容量与最低岗位|
|POST /zone-posts|admin/steward安排已到岗人员岗位|
|POST /house-incidents、/{id}/resolve|admin/steward登记事件与处置说明|
|POST /house-incidents/{id}/dispatch、/{id}/close|仅admin分派和复核关闭|
|POST /lost-items、POST /item-claims、PUT /item-claims/{id}|admin/steward保管、认领与凭据更正|
|POST /item-claims/{id}/handover|仅admin核验交付|

`zone_models.py`、`incident_models.py`、`lost_models.py`保存五张独立关系表；`zones_service.py`、`incidents_service.py`、`lost_service.py`实现容量/岗位、事件升级和唯一交付；`house_schemas.py`与`house_routes.py`提供请求/权限/事务。`debrief_service.py`对新保存检查岗位，对新归档检查高风险事件；无历史回填、原表无新增列。前端 `pages/zones.js`、`incidents.js`、`lost.js`三页共享 `utils/house.js` 的场次选择，保留原六页。事件枚举在前后端constants。

seed为交接演练夜场/午场分别提供EAST/WEST各80容量、最低1岗；不自动分配岗位。剧本：到岗人员沈青/唐禾分别安排两区→登记拥堵高风险→经理分派→现场说明→经理关闭→散场归档；西入口拾到棕色钱包→登记不公开特征→认领人提供描述→经理核对交付。反复seed不覆盖人工岗位、事件处置、认领凭据或原交接。

当前范围：分区配置为固定记录，无临时撤岗/跨区调度/分区删除；要求的最低人数由经理给定。事件不通知外部医疗或安保，不是紧急呼救系统；处置由场务角色代录，未对齐个人登录身份。失物凭据按去首尾空白、不区分字母大小写的完整特征文本匹配，用于演示经理核对，无证件/照片识别或外部认领消息；认领姓名/凭据留本地数据库。原人工签到和运营演练数据范围继续适用。新证据在 `test-artifacts/gb-1025/v3/`。

MIT License。
