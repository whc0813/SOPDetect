const PptxGenJS = require("pptxgenjs");
const { warnIfSlideHasOverlaps, warnIfSlideElementsOutOfBounds } = require("./pptxgenjs_helpers/layout.js");

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";

const SW = 10;   // slide width  (inches, LAYOUT_WIDE)
const SH = 7.5;  // slide height (inches, LAYOUT_WIDE)

const F  = "Microsoft YaHei";
const C  = {
  black:  "111111",
  dark:   "333333",
  mid:    "666666",
  light:  "999999",
  line:   "DDDDDD",
  bg:     "F7F7F7",
  white:  "FFFFFF",
  accent: "1A56DB",   // single brand blue
  accentL:"EBF1FD",   // light tint
  red:    "D0220A",
  amber:  "C47A00",
  green:  "1A7A3A",
};

// ─── helpers ──────────────────────────────────────────────────────────────────

function slide_base(title, pageNum) {
  const s = pptx.addSlide();
  // white bg
  s.addShape(pptx.ShapeType.rect, { x:0, y:0, w:SW, h:SH, fill:{color:C.white}, line:{type:"none"} });
  // thin top rule
  s.addShape(pptx.ShapeType.rect, { x:0, y:0, w:SW, h:0.04, fill:{color:C.accent}, line:{type:"none"} });
  // title
  s.addText(title, {
    x:0.5, y:0.2, w:SW-1, h:0.7,
    fontFace:F, fontSize:20, bold:true, color:C.black,
  });
  // thin divider below title
  s.addShape(pptx.ShapeType.rect, { x:0.5, y:0.95, w:SW-1, h:0.02, fill:{color:C.line}, line:{type:"none"} });
  // page number
  s.addText(`${pageNum}`, {
    x:SW-0.6, y:SH-0.5, w:0.5, h:0.3,
    fontFace:F, fontSize:9, color:C.light, align:"right",
  });
  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
  return s;
}

// content area starts at y=1.1, height = 6.0
const CY = 1.1;
const CH = 6.0;

function bul(text, size=12.5, color=C.dark) {
  return { text, options:{ bullet:{type:"bullet"}, fontFace:F, fontSize:size, color, breakLine:true, paraSpaceAfter:4 } };
}

// draw a simple labeled box
function box(s, x, y, w, h, label, labelColor=C.accent, bgColor=C.accentL, borderColor=C.accent) {
  s.addShape(pptx.ShapeType.rect, { x, y, w, h, fill:{color:bgColor}, line:{color:borderColor, pt:0.8} });
  if (label) {
    s.addText(label, {
      x:x+0.1, y:y+0.08, w:w-0.2, h:0.38,
      fontFace:F, fontSize:11, bold:true, color:labelColor,
    });
  }
}

// placeholder for a screenshot
function screenshot_box(s, x, y, w, h, caption) {
  s.addShape(pptx.ShapeType.rect, { x, y, w, h, fill:{color:C.bg}, line:{color:C.line, pt:1} });
  s.addText("[ 截图区域 ]", {
    x, y:y + h/2 - 0.3, w, h:0.35,
    fontFace:F, fontSize:12, color:C.light, align:"center", bold:false,
  });
  if (caption) {
    s.addText(caption, {
      x, y:y+h+0.05, w, h:0.3,
      fontFace:F, fontSize:10, color:C.mid, align:"center",
    });
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 1  封面
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.addShape(pptx.ShapeType.rect, { x:0, y:0, w:SW, h:SH, fill:{color:C.white}, line:{type:"none"} });
  // left accent strip
  s.addShape(pptx.ShapeType.rect, { x:0, y:0, w:0.08, h:SH, fill:{color:C.accent}, line:{type:"none"} });
  // title
  s.addText("基于视觉分析的标准操作流程\n管理与视频评估系统", {
    x:0.6, y:1.8, w:8.6, h:2.0,
    fontFace:F, fontSize:32, bold:true, color:C.black, align:"left",
  });
  // rule
  s.addShape(pptx.ShapeType.rect, { x:0.6, y:3.9, w:3.0, h:0.04, fill:{color:C.accent}, line:{type:"none"} });
  // subtitle
  s.addText("毕业设计中期检查报告", {
    x:0.6, y:4.1, w:8, h:0.5,
    fontFace:F, fontSize:16, bold:false, color:C.mid, align:"left",
  });
  s.addText("汇报人：王鸿灿   指导教师：XXX   2026 年 4 月", {
    x:0.6, y:5.0, w:8, h:0.4,
    fontFace:F, fontSize:12, color:C.light, align:"left",
  });
  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 2  目录
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("目录", 2);
  const items = [
    "01   系统整体架构",
    "02   项目进度总览",
    "03   已实现功能 — 用户与权限管理",
    "04   已实现功能 — SOP 创建与管理",
    "05   已实现功能 — 三阶段视频评估算法",
    "06   已实现功能 — 异步评估任务队列",
    "07   已实现功能 — 历史记录与人工复核",
    "08   系统界面截图展示",
    "09   接口设计",
    "10   数据库设计",
    "11   存在的问题与改进措施",
    "12   下一阶段计划",
  ];
  const half = Math.ceil(items.length / 2);
  items.forEach((txt, i) => {
    const col = i < half ? 0 : 1;
    const row = i < half ? i : i - half;
    const x = 0.5 + col * 4.7;
    const y = CY + 0.1 + row * 0.47;
    const isAccent = i === 0;
    s.addText(txt, {
      x, y, w:4.4, h:0.42,
      fontFace:F, fontSize:13, color: isAccent ? C.accent : C.dark,
      bold:false,
    });
    s.addShape(pptx.ShapeType.rect, { x, y:y+0.39, w:4.4, h:0.01, fill:{color:C.line}, line:{type:"none"} });
  });
  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 3  系统整体架构
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("01   系统整体架构", 3);

  const layers = [
    { label:"浏览器前端   Vue 3 + Element Plus", y:1.25, color:C.accentL, tc:C.accent },
    { label:"后端 API 服务   FastAPI + Uvicorn", y:2.35, color:"F0FDF4", tc:"166534" },
    { label:"评估 Worker   异步任务队列  ·  三阶段评估 Pipeline", y:3.45, color:"FFFBEB", tc:"92400E" },
  ];
  layers.forEach(({ label, y, color, tc }) => {
    s.addShape(pptx.ShapeType.rect, { x:1.0, y, w:8.0, h:0.8, fill:{color}, line:{color:C.line, pt:0.8} });
    s.addText(label, { x:1.15, y, w:7.7, h:0.8, fontFace:F, fontSize:13, bold:true, color:tc, valign:"middle" });
  });

  // bottom two
  const bot = [
    { label:"多模态大模型 API\nOpenAI 兼容 / DashScope", x:1.0, w:3.8, color:"F5F3FF", tc:"4C1D95" },
    { label:"MySQL 8\n本地媒体存储", x:5.2, w:3.8, color:"FFF0F0", tc:"7F1D1D" },
  ];
  bot.forEach(({ label, x, w, color, tc }) => {
    s.addShape(pptx.ShapeType.rect, { x, y:4.55, w, h:0.9, fill:{color}, line:{color:C.line, pt:0.8} });
    s.addText(label, { x:x+0.1, y:4.55, w:w-0.2, h:0.9, fontFace:F, fontSize:12, bold:true, color:tc, align:"center", valign:"middle" });
  });

  // connector arrows (just short vertical lines)
  [1.65, 2.75, 3.85].forEach(y => {
    s.addShape(pptx.ShapeType.line, { x:5.0, y, w:0, h:0.08, line:{color:C.mid, pt:1} });
  });

  // tech stack notes
  const notes = [
    { t:"Vue Router · httpx · sessionStorage", y:1.38 },
    { t:"Pydantic v2 · PyMySQL · OpenCV", y:2.48 },
    { t:"多线程轮询 · JSON Schema 约束输出", y:3.58 },
  ];
  notes.forEach(({ t, y }) => {
    s.addText(t, { x:0.5, y, w:0.45, h:0.58, fontFace:F, fontSize:7.5, color:C.light, wrap:true });
  });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 4  项目进度总览
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("02   项目进度总览", 4);

  const phases = [
    { name:"需求分析 & 技术选型",     period:"2025.11–12", pct:100, done:true },
    { name:"后端核心 API 与数据库",    period:"2025.12–2026.01", pct:100, done:true },
    { name:"三阶段评估算法实现",       period:"2026.01–03", pct:100, done:true },
    { name:"前端界面开发与联调",       period:"2026.02–03", pct:90,  done:false },
    { name:"评测过程可视化增强",       period:"2026.04",   pct:30,  done:false },
    { name:"系统测试 & 性能优化",      period:"2026.04–05", pct:10, done:false },
    { name:"论文撰写 & 最终答辩",      period:"2026.05–06", pct:5,  done:false },
  ];

  const bx = 3.4, bw = 5.6, rh = 0.74, sy = CY + 0.15;

  phases.forEach(({ name, period, pct, done }, i) => {
    const y = sy + i * rh;
    const barColor = done ? C.accent : (pct >= 10 ? C.amber : C.light);
    const labelColor = done ? C.accent : (pct === 100 ? C.accent : C.dark);

    // row label
    s.addText(name, { x:0.5, y:y+0.08, w:2.75, h:0.38, fontFace:F, fontSize:11.5, color:labelColor });
    s.addText(period, { x:0.5, y:y+0.44, w:2.75, h:0.22, fontFace:F, fontSize:9, color:C.light });

    // bar bg
    s.addShape(pptx.ShapeType.rect, { x:bx, y:y+0.15, w:bw, h:0.34, fill:{color:C.bg}, line:{type:"none"} });
    // bar fill
    if (pct > 0) {
      s.addShape(pptx.ShapeType.rect, { x:bx, y:y+0.15, w:bw*(pct/100), h:0.34, fill:{color:barColor}, line:{type:"none"} });
    }
    // pct label
    s.addText(`${pct}%`, { x:bx+bw+0.1, y:y+0.15, w:0.55, h:0.34, fontFace:F, fontSize:11, bold:done, color:barColor });
  });

  // current marker
  s.addShape(pptx.ShapeType.line, {
    x:bx + bw*0.88, y:sy-0.1, w:0, h:phases.length*rh,
    line:{color:C.red, pt:1, dashType:"dash"},
  });
  s.addText("当前", { x:bx+bw*0.88-0.25, y:sy-0.38, w:0.8, h:0.25, fontFace:F, fontSize:9, color:C.red, bold:true });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 5  用户与权限管理
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("03   已实现功能 — 用户与权限管理", 5);

  const items = [
    { title:"用户注册 / 登录",  desc:"用户名 + 密码注册登录，后端返回 Bearer Token；前端用 sessionStorage 管理会话，支持跨标签页同步" },
    { title:"单活跃会话",       desc:"每账号仅允许一个活跃 session；新登录自动踢出旧会话，防止并发冲突" },
    { title:"双角色权限分离",   desc:"admin / user 两种角色；前端路由守卫 + 后端接口鉴权双层校验，禁止越权访问" },
    { title:"管理员用户管理",   desc:"管理员可查看全部用户列表、启用 / 禁用账号，操作实时生效" },
  ];

  items.forEach(({ title, desc }, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.5 + col * 4.8, y = CY + 0.2 + row * 2.65;
    s.addShape(pptx.ShapeType.rect, { x, y, w:4.5, h:2.45, fill:{color:C.bg}, line:{color:C.line, pt:0.8} });
    s.addShape(pptx.ShapeType.rect, { x, y, w:0.06, h:2.45, fill:{color:C.accent}, line:{type:"none"} });
    s.addText(title, { x:x+0.2, y:y+0.15, w:4.1, h:0.4, fontFace:F, fontSize:13, bold:true, color:C.black });
    s.addText(desc,  { x:x+0.2, y:y+0.65, w:4.1, h:1.65, fontFace:F, fontSize:12, color:C.dark, wrap:true });
  });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 6  SOP 创建与管理
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("04   已实现功能 — SOP 创建与管理", 6);

  const items = [
    { title:"SOP CRUD",            desc:"创建、查看、删除 SOP；步骤支持必要 / 可选 / 条件三种类型及前置依赖关系" },
    { title:"工作流视频自动分割",   desc:"上传整段示范视频后，AI 自动预估各步骤时间范围，按区间抽帧并构建参考包（摘要、ROI、关键时刻）" },
    { title:"单步示范视频替换",     desc:"管理员可对指定步骤单独替换示范视频，系统重新抽帧并更新参考包，无需重建整个 SOP" },
    { title:"手动时间戳覆盖",       desc:"支持手动修正步骤时间段，覆盖 AI 自动分割结果，适用于精细化场景" },
    { title:"评分权重与惩罚配置",   desc:"每个 SOP 可配置步骤权重及 penaltyConfig 惩罚规则，评估完成后自动加权计算综合得分" },
    { title:"API 配置管理",         desc:"管理员可在前端配置 AI 模型参数（Key、BaseURL、模型名、fps、temperature 等），实时生效" },
  ];

  const cw = 2.95, rh = 1.7, sx = 0.45, sy = CY + 0.15;
  items.forEach(({ title, desc }, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = sx + col*(cw+0.1), y = sy + row*(rh+0.2);
    s.addShape(pptx.ShapeType.rect, { x, y, w:cw, h:rh, fill:{color:C.bg}, line:{color:C.line, pt:0.8} });
    s.addText(title, { x:x+0.12, y:y+0.1, w:cw-0.24, h:0.4, fontFace:F, fontSize:11.5, bold:true, color:C.accent });
    s.addText(desc,  { x:x+0.12, y:y+0.55, w:cw-0.24, h:rh-0.65, fontFace:F, fontSize:10.5, color:C.dark, wrap:true });
  });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 7  三阶段评估算法
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("05   已实现功能 — 三阶段视频评估算法", 7);

  // flow boxes
  const stages = [
    { num:"1", label:"时序分段", en:"Temporal Segmentation", color:"EBF1FD", tc:C.accent },
    { num:"2", label:"批量逐步评估", en:"Per-Step Evaluation", color:"F0FDF4", tc:"166534" },
    { num:"3", label:"全局校验", en:"Global Validation", color:"FFFBEB", tc:"92400E" },
    { num:"4", label:"后处理评分", en:"Post-process Scoring", color:"F5F3FF", tc:"4C1D95" },
  ];
  const bw = 1.9, bh = 1.1, sy = CY + 0.2, gap = 0.22;
  const totalW = stages.length*bw + (stages.length-1)*gap;
  const sx = (SW - totalW) / 2;

  stages.forEach(({ num, label, en, color, tc }, i) => {
    const x = sx + i*(bw+gap);
    s.addShape(pptx.ShapeType.rect, { x, y:sy, w:bw, h:bh, fill:{color}, line:{color:C.line, pt:0.8} });
    s.addText(`${num}`, { x, y:sy+0.08, w:bw, h:0.4, fontFace:F, fontSize:18, bold:true, color:tc, align:"center" });
    s.addText(label, { x, y:sy+0.52, w:bw, h:0.32, fontFace:F, fontSize:12, bold:true, color:tc, align:"center" });
    s.addText(en,    { x, y:sy+0.82, w:bw, h:0.24, fontFace:F, fontSize:8.5, color:C.light, align:"center" });
    if (i < stages.length-1) {
      s.addShape(pptx.ShapeType.line, { x:x+bw+0.02, y:sy+bh/2, w:gap-0.04, h:0, line:{color:C.line, pt:1.5} });
    }
  });

  // detail rows
  const details = [
    { stage:"Stage 1", points:[
      "以可配置 fps 从用户执行视频采样帧",
      "单次调用多模态大模型，输出各步骤起止帧索引",
      "调用失败时自动 fallback：均匀切分视频作为缺省分段",
    ]},
    { stage:"Stage 2", points:[
      "整段视频 + 所有步骤描述 + Stage 1 时序上下文，一次调用完成",
      "JSON Schema 约束输出格式：是否完成、问题类型、描述、置信度",
      "进度实时写回 evaluation_job 表，前端可轮询",
    ]},
    { stage:"Stage 3 + 后处理", points:[
      "全局校验步骤顺序与前置条件约束，结果可覆盖 Stage 2 单步判断",
      "读取 penaltyConfig 与步骤权重，计算加权综合分",
      "输出：综合评分 / 通过状态 / 各步骤明细 + 问题说明",
    ]},
  ];

  const dy = sy + bh + 0.35, dh = 1.55, dw = (SW-1.0)/3;
  details.forEach(({ stage, points }, i) => {
    const x = 0.5 + i*(dw+0.1);
    s.addText(stage, { x, y:dy, w:dw, h:0.32, fontFace:F, fontSize:11, bold:true, color:C.dark });
    s.addText(points.map(p => bul(p, 10.5, C.dark)), { x, y:dy+0.35, w:dw, h:dh-0.35, fontFace:F });
  });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 8  异步评估任务队列
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("06   已实现功能 — 异步评估任务队列", 8);

  const steps = [
    { label:"提交任务",  desc:"前端调用 POST /api/sops/{id}/evaluation-jobs，视频与元数据入库，返回 job_id" },
    { label:"Worker 领取", desc:"后台 Worker 线程每 2 s 轮询，原子化领取任务，避免重复执行" },
    { label:"执行评估",  desc:"构造媒体 data URL → 依次执行 Stage 1 / 2 / 3 → 进度写回数据库" },
    { label:"结果持久化", desc:"评估完成后写入 sop_executions / execution_step_results / execution_issues" },
    { label:"失败重试",  desc:"POST /retry 手动重试；任务状态枚举：pending → running → completed / failed" },
  ];

  const bw = 1.55, bh = 0.48, gapX = 0.12;
  const totalW = steps.length*bw + (steps.length-1)*gapX;
  const startX = (SW - totalW) / 2;
  const flowY = CY + 0.35;

  steps.forEach(({ label }, i) => {
    const x = startX + i*(bw+gapX);
    // intentional: text sits on colored shape (badge style)
    s.addShape(pptx.ShapeType.rect, { x, y:flowY, w:bw, h:bh, fill:{color:C.accent}, line:{type:"none"} });
    s.addText(`${i+1}. ${label}`, { x:x+0.05, y:flowY+0.05, w:bw-0.1, h:bh-0.1, fontFace:F, fontSize:11, bold:true, color:C.white, align:"center", valign:"middle" });
    if (i < steps.length-1) {
      s.addShape(pptx.ShapeType.line, { x:x+bw+0.01, y:flowY+bh/2, w:gapX-0.02, h:0, line:{color:C.mid, pt:1.2} });
    }
  });

  // desc cards
  const cardH = 4.5, cardY = flowY + bh + 0.5;
  steps.forEach(({ label, desc }, i) => {
    const x = startX + i*(bw+gapX);
    s.addShape(pptx.ShapeType.rect, { x, y:cardY, w:bw, h:cardH, fill:{color:C.bg}, line:{color:C.line, pt:0.8} });
    s.addText(desc, { x:x+0.08, y:cardY+0.12, w:bw-0.16, h:cardH-0.24, fontFace:F, fontSize:10.5, color:C.dark, wrap:true });
  });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 9  历史记录与人工复核
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("07   已实现功能 — 历史记录与人工复核", 9);

  const items = [
    { title:"多条件筛选", desc:"支持关键词、AI 评估状态、人工复核状态多维度过滤，结果按时间排序" },
    { title:"步骤级详情", desc:"历史详情页展示综合分、通过状态、每个步骤的结论、问题类型和问题描述" },
    { title:"人工复核",   desc:"管理员可标注复核结论（通过 / 不通过 / 需改进）及备注，形成质检闭环" },
    { title:"数据统计",   desc:"管理员统计面板提供总评估次数、通过率、各 SOP 评估量分布" },
  ];

  items.forEach(({ title, desc }, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.5 + col*4.8, y = CY + 0.2 + row*2.65;
    s.addShape(pptx.ShapeType.rect, { x, y, w:4.5, h:2.45, fill:{color:C.bg}, line:{color:C.line, pt:0.8} });
    s.addShape(pptx.ShapeType.rect, { x, y, w:0.06, h:2.45, fill:{color:C.accent}, line:{type:"none"} });
    s.addText(title, { x:x+0.2, y:y+0.15, w:4.1, h:0.4, fontFace:F, fontSize:13, bold:true, color:C.black });
    s.addText(desc,  { x:x+0.2, y:y+0.65, w:4.1, h:1.65, fontFace:F, fontSize:12, color:C.dark, wrap:true });
  });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 10  系统界面截图展示
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("08   系统界面截图展示", 10);

  // 4 screenshot placeholders in 2×2 grid
  const captions = [
    "管理员 - SOP 列表与创建",
    "管理员 - 评估历史与复核",
    "用户端 - 提交评估任务",
    "用户端 - 评估结果详情",
  ];
  const pw = 4.45, ph = 2.7, gap = 0.1;
  captions.forEach((cap, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.5 + col*(pw+gap);
    const y = CY + 0.1 + row*(ph+0.42);
    // box
    s.addShape(pptx.ShapeType.rect, { x, y, w:pw, h:ph, fill:{color:C.bg}, line:{color:C.line, pt:1} });
    s.addText("[ 截图区域 ]", { x, y:y+ph/2-0.2, w:pw, h:0.35, fontFace:F, fontSize:12, color:C.light, align:"center" });
    // caption below, within slide
    s.addText(cap, { x, y:y+ph+0.04, w:pw, h:0.28, fontFace:F, fontSize:10, color:C.mid, align:"center" });
  });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 11  接口设计
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("09   接口设计", 11);

  const apis = [
    { group:"认证",   color:"EBF1FD", tc:C.accent, items:[
      "POST /api/auth/login          用户登录，返回 Bearer Token",
      "POST /api/auth/register       用户注册",
      "GET  /api/auth/me             获取当前登录用户信息",
    ]},
    { group:"SOP 管理", color:"F0FDF4", tc:"166534", items:[
      "GET/POST /api/sops            SOP 列表查询 / 创建新 SOP",
      "DELETE   /api/sops/{id}       删除指定 SOP",
      "POST /api/sops/{id}/segment-video   上传整段示范视频并触发 AI 分割",
      "POST /api/sops/{id}/steps/{sid}/replace-video   替换单步示范视频",
      "POST /api/sops/{id}/manual-segmentation-override   手动覆盖时间段",
    ]},
    { group:"评估任务", color:"FFFBEB", tc:"92400E", items:[
      "POST /api/sops/{id}/evaluation-jobs    提交异步评估任务",
      "GET  /api/evaluation-jobs              查询评估任务列表",
      "GET  /api/evaluation-jobs/{job_id}     查询单个任务状态与进度",
      "POST /api/evaluation-jobs/{job_id}/retry   重试失败任务",
    ]},
    { group:"历史 & 统计", color:"F5F3FF", tc:"4C1D95", items:[
      "GET  /api/executions          历史记录列表（支持多条件筛选）",
      "GET  /api/executions/{id}     历史详情（步骤级结果）",
      "PUT  /api/executions/{id}/review   管理员提交人工复核",
      "GET  /api/stats               管理员统计数据（通过率、评估量等）",
    ]},
  ];

  const colW = 4.45, rh = 2.95;
  apis.forEach(({ group, color, tc, items }, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.5 + col*(colW+0.1), y = CY + 0.1 + row*(rh+0.15);
    s.addShape(pptx.ShapeType.rect, { x, y, w:colW, h:rh, fill:{color}, line:{color:C.line, pt:0.8} });
    s.addText(group, { x:x+0.12, y:y+0.08, w:colW-0.24, h:0.34, fontFace:F, fontSize:11.5, bold:true, color:tc });
    s.addShape(pptx.ShapeType.rect, { x:x+0.12, y:y+0.44, w:colW-0.24, h:0.01, fill:{color:C.line}, line:{type:"none"} });
    s.addText(
      items.map(t => ({ text:t, options:{ bullet:{type:"bullet"}, fontFace:"Consolas", fontSize:9.5, color:C.dark, breakLine:true, paraSpaceAfter:3 } })),
      { x:x+0.12, y:y+0.52, w:colW-0.24, h:rh-0.6, fontFace:F }
    );
  });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 12  数据库设计
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("10   数据库设计", 12);

  const groups = [
    { name:"用户与认证",  color:"EBF1FD", tc:C.accent, tables:[
      { t:"users",                 desc:"用户基本信息、角色、状态" },
      { t:"user_login_sessions",   desc:"活跃会话 Token（单活跃策略）" },
      { t:"ai_configs",            desc:"AI 模型配置（Key 加密存储）" },
    ]},
    { name:"SOP 主数据",  color:"F0FDF4", tc:"166534", tables:[
      { t:"sops",                  desc:"SOP 元数据（名称、描述、惩罚配置）" },
      { t:"sop_steps",             desc:"步骤详情（类型、权重、前置、描述）" },
      { t:"sop_step_prerequisites",desc:"步骤前置依赖关系" },
    ]},
    { name:"媒体与参考",  color:"FFFBEB", tc:"92400E", tables:[
      { t:"media_files",           desc:"媒体文件索引与本地路径" },
      { t:"sop_step_keyframes",    desc:"步骤参考关键帧及 ROI 区域" },
      { t:"sop_step_substeps",     desc:"步骤关键时刻（AI 生成摘要）" },
    ]},
    { name:"评估任务",    color:"F5F3FF", tc:"4C1D95", tables:[
      { t:"evaluation_jobs",       desc:"异步任务状态与进度" },
      { t:"evaluation_job_logs",   desc:"任务执行日志（阶段级）" },
    ]},
    { name:"执行结果",    color:"FFF0F0", tc:"7F1D1D", tables:[
      { t:"sop_executions",          desc:"整体执行记录（综合分、通过状态）" },
      { t:"execution_step_results",  desc:"步骤级评估结论" },
      { t:"execution_issues",        desc:"步骤级问题明细与描述" },
    ]},
    { name:"人工复核",    color:"F7FEE7", tc:"3F6212", tables:[
      { t:"manual_reviews",          desc:"复核结论、备注、复核人" },
    ]},
  ];

  const cw = 2.95, rh = 2.6, gap = 0.1, sx = 0.45, sy = CY + 0.1;
  groups.forEach(({ name, color, tc, tables }, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = sx + col*(cw+gap), y = sy + row*(rh+0.1);
    s.addShape(pptx.ShapeType.rect, { x, y, w:cw, h:rh, fill:{color}, line:{color:C.line, pt:0.8} });
    s.addText(name, { x:x+0.1, y:y+0.08, w:cw-0.2, h:0.34, fontFace:F, fontSize:11, bold:true, color:tc });
    s.addShape(pptx.ShapeType.rect, { x:x+0.1, y:y+0.44, w:cw-0.2, h:0.01, fill:{color:C.line}, line:{type:"none"} });
    tables.forEach(({ t, desc }, j) => {
      const ty = y + 0.52 + j*0.65;
      s.addText(t, { x:x+0.1, y:ty, w:cw-0.2, h:0.28, fontFace:"Consolas", fontSize:10, bold:true, color:C.dark });
      s.addText(desc, { x:x+0.1, y:ty+0.28, w:cw-0.2, h:0.3, fontFace:F, fontSize:9.5, color:C.mid });
    });
  });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 13  存在的问题
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("11   存在的问题与改进措施", 13);

  const problems = [
    { id:"P1", title:"时序分段准确率依赖帧率与视频质量",
      prob:"Stage 1 按固定 fps 抽帧，动作切换不明显时难以准确判断步骤边界，导致分段区间偏移。",
      fix:"引入自适应帧率策略；在 Prompt 中加入帧差异提示；为步骤设定时长约束作为后验规则。",
      level:"高" },
    { id:"P2", title:"批量评估 Prompt 过长时可能被模型截断",
      prob:"Stage 2 将所有步骤与完整视频帧合并为单一请求，步骤多 / 视频长时逼近上下文窗口限制。",
      fix:"实现动态分批策略自动拆分；对相邻相似帧去重；用步骤摘要替换原始描述压缩 Token。",
      level:"高" },
    { id:"P3", title:"工作流视频自动分割结果不稳定",
      prob:"AI 输出存在随机性，相同视频多次分割可能得到差异较大的区间，参考包一致性较低。",
      fix:"分割阶段降低 temperature；多次采样取众数；提供管理员拖拽微调界面。",
      level:"中" },
    { id:"P4", title:"评测过程对用户不透明",
      prob:"历史详情页仅展示最终评分，三阶段中间推理过程对用户不可见，降低了系统可信度。",
      fix:"历史详情增加三阶段折叠面板；时间轴展示每步被定位到的时间段。",
      level:"中" },
    { id:"P5", title:"评估结论缺少视频时间戳定位",
      prob:"步骤结论没有关联到视频的具体时间段，用户无法快速定位问题位置，复核成本高。",
      fix:"将 Stage 1 分段结果关联到步骤结论；EvalTimeline 支持点击跳转到对应时间点。",
      level:"中" },
  ];

  const rh = 1.02, sx = 0.5, sy = CY + 0.05;
  const lColors = { "高":C.red, "中":C.amber };

  problems.forEach(({ id, title, prob, fix, level }, i) => {
    const y = sy + i * rh;
    const lc = lColors[level] || C.light;

    // row bg (alternating)
    s.addShape(pptx.ShapeType.rect, { x:sx, y, w:SW-1, h:rh-0.04, fill:{color: i%2===0?C.white:C.bg}, line:{type:"none"} });
    // left border
    s.addShape(pptx.ShapeType.rect, { x:sx, y, w:0.04, h:rh-0.04, fill:{color:lc}, line:{type:"none"} });

    // ID + level badge
    s.addText(id, { x:sx+0.1, y:y+0.05, w:0.38, h:0.3, fontFace:F, fontSize:10.5, bold:true, color:lc });
    s.addText(level, { x:sx+0.1, y:y+0.37, w:0.38, h:0.22, fontFace:F, fontSize:8, color:lc });

    // title
    s.addText(title, { x:sx+0.55, y:y+0.04, w:8.4, h:0.32, fontFace:F, fontSize:12, bold:true, color:C.black });

    // prob
    s.addText("问题  " + prob, { x:sx+0.55, y:y+0.38, w:4.0, h:0.54, fontFace:F, fontSize:10, color:C.mid, wrap:true });
    // fix
    s.addText("改进  " + fix,  { x:sx+4.6,  y:y+0.38, w:4.3, h:0.54, fontFace:F, fontSize:10, color:C.dark, wrap:true });
  });

  // column headers
  s.addText("问题描述", { x:sx+0.55, y:sy-0.28, w:4.0, h:0.24, fontFace:F, fontSize:9.5, bold:true, color:C.light });
  s.addText("改进措施", { x:sx+4.6,  y:sy-0.28, w:4.3, h:0.24, fontFace:F, fontSize:9.5, bold:true, color:C.light });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 14  下一阶段计划
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = slide_base("12   下一阶段工作计划", 14);

  const plans = [
    { period:"4 月（当前）", tasks:[
      "完成评测过程可视化：历史详情增加三阶段展示面板",
      "EvalTimeline 支持步骤时间段跳转",
      "修复时序分段 fallback 策略已知缺陷",
    ]},
    { period:"5 月上旬", tasks:[
      "实现动态分批评估，解决长视频 Prompt 过长问题",
      "关键帧相似度去重模块，降低 Token 成本",
      "条件步骤结构化配置模板与预览测试",
    ]},
    { period:"5 月中旬–下旬", tasks:[
      "端到端全场景压力测试",
      "优化评估响应时延，目标 P90 < 60 s",
      "前端界面打磨与错误提示优化",
    ]},
    { period:"6 月", tasks:[
      "撰写毕业论文：系统设计、算法描述、实验数据分析",
      "准备答辩演示材料与演示视频",
      "代码整理与文档归档",
    ]},
  ];

  const cw = 4.45, ch = 2.65, gap = 0.1, sx = 0.5, sy = CY + 0.15;
  plans.forEach(({ period, tasks }, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = sx + col*(cw+gap), y = sy + row*(ch+0.2);
    s.addShape(pptx.ShapeType.rect, { x, y, w:cw, h:ch, fill:{color:C.bg}, line:{color:C.line, pt:0.8} });
    s.addShape(pptx.ShapeType.rect, { x, y, w:cw, h:0.38, fill:{color:C.accent}, line:{type:"none"} });
    s.addText(period, { x:x+0.12, y, w:cw-0.24, h:0.38, fontFace:F, fontSize:12, bold:true, color:C.white, valign:"middle" });
    s.addText(tasks.map(t => bul(t, 11.5, C.dark)), { x:x+0.12, y:y+0.45, w:cw-0.24, h:ch-0.55, fontFace:F });
  });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 15  总结
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pptx.addSlide();
  s.addShape(pptx.ShapeType.rect, { x:0, y:0, w:SW, h:SH, fill:{color:C.white}, line:{type:"none"} });
  s.addShape(pptx.ShapeType.rect, { x:0, y:0, w:0.08, h:SH, fill:{color:C.accent}, line:{type:"none"} });

  s.addText("总结", { x:0.5, y:1.2, w:8, h:0.7, fontFace:F, fontSize:24, bold:true, color:C.black });
  s.addShape(pptx.ShapeType.rect, { x:0.5, y:1.95, w:1.5, h:0.03, fill:{color:C.accent}, line:{type:"none"} });

  const points = [
    ["系统核心功能已基本完成", "用户权限管理、SOP 管理、三阶段评估算法、异步任务队列、历史记录与人工复核均已实现并联调"],
    ["技术难点已有成熟方案",   "三阶段 Pipeline 有效解耦分段、评估、校验三个子问题，具备良好扩展性"],
    ["问题与改进方向明确",     "识别 5 个核心问题，均有具体改进措施，按优先级有序推进"],
    ["后续工作可按期完成",     "4–5 月功能完善与测试，6 月完成论文撰写，时间节点清晰"],
  ];

  points.forEach(([title, desc], i) => {
    const y = 2.3 + i * 1.15;
    s.addText(`0${i+1}`, { x:0.5, y, w:0.45, h:0.45, fontFace:F, fontSize:16, bold:true, color:C.accent, align:"center", valign:"middle" });
    s.addText(title, { x:1.1, y, w:8.3, h:0.38, fontFace:F, fontSize:13.5, bold:true, color:C.black });
    s.addText(desc,  { x:1.1, y:y+0.42, w:8.3, h:0.55, fontFace:F, fontSize:12, color:C.mid });
  });

  s.addText("感谢聆听，请批评指正", { x:0.5, y:SH-0.55, w:8, h:0.35, fontFace:F, fontSize:13, color:C.light });

  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
}

// ─── Save ─────────────────────────────────────────────────────────────────────
pptx.writeFile({ fileName: "D:/毕业设计/ppt_workspace/中期检查PPT.pptx" }).then(() => {
  console.log("Done: D:/毕业设计/ppt_workspace/中期检查PPT.pptx");
});
