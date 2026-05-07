const path = require("path");
const PptxGenJS = require("pptxgenjs");
const {
  autoFontSize,
  calcTextBox,
  svgToDataUri,
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
} = require("./pptxgenjs_helpers");

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "OpenAI Codex";
pptx.company = "毕业设计";
pptx.subject = "毕业设计中期检查";
pptx.title = "基于视觉分析的标准操作流程（SOP）管理系统设计与实现";
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: "Microsoft YaHei",
  bodyFontFace: "Microsoft YaHei",
  lang: "zh-CN",
};

const SW = 13.333;
const SH = 7.5;
const M = 0.55;

const C = {
  navy: "113A8F",
  blue: "2F6BFF",
  cyan: "3AA7FF",
  teal: "2C8C7A",
  green: "2AA876",
  amber: "E3A008",
  red: "D64545",
  text: "1E2A39",
  subtext: "5C6B80",
  line: "D6E0F3",
  panel: "F7FAFF",
  panel2: "EEF4FF",
  white: "FFFFFF",
  dark: "0C1C3A",
};

const deckDir = __dirname;
const outputFile = path.join(deckDir, "毕业设计中期检查_修订版_功能模块标注.pptx");

function addBg(slide, dark = false) {
  const bg = dark ? C.dark : C.white;
  slide.background = { color: bg };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: SW,
    h: SH,
    line: { color: bg, transparency: 100 },
    fill: { color: bg },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: SW,
    h: 0.06,
    line: { color: dark ? C.cyan : C.blue, transparency: 100 },
    fill: { color: dark ? C.cyan : C.blue },
  });
}

function addFooter(slide, pageNo) {
  slide.addShape(pptx.ShapeType.line, {
    x: M,
    y: SH - 0.45,
    w: SW - M * 2 - 0.7,
    h: 0,
    line: { color: C.line, width: 1 },
  });
  slide.addText("毕业设计中期检查", {
    x: M,
    y: SH - 0.36,
    w: 2.4,
    h: 0.16,
    fontFace: "Microsoft YaHei",
    fontSize: 8.5,
    color: C.subtext,
    margin: 0,
  });
  slide.addText(String(pageNo), {
    x: SW - 0.8,
    y: SH - 0.38,
    w: 0.28,
    h: 0.18,
    align: "right",
    fontFace: "Microsoft YaHei",
    fontSize: 9,
    bold: true,
    color: C.navy,
    margin: 0,
  });
}

function addTitle(slide, title, subtitle = "") {
  slide.addText(title, {
    x: M,
    y: 0.42,
    w: 8.2,
    h: 0.45,
    fontFace: "Microsoft YaHei",
    fontSize: 24,
    bold: true,
    color: C.text,
    margin: 0,
  });
  if (subtitle) {
    const h = calcTextBox(10.5, {
      text: subtitle,
      w: 5.5,
      fontFace: "Microsoft YaHei",
      margin: 0,
      padding: 0.06,
      leading: 1.25,
    }).h;
    slide.addText(subtitle, {
      x: M,
      y: 0.9,
      w: 5.5,
      h,
      fontFace: "Microsoft YaHei",
      fontSize: 10.5,
      color: C.subtext,
      margin: 0,
      breakLine: false,
      valign: "top",
    });
  }
}

function addPill(slide, text, x, y, w, color, textColor = C.white) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 0.32,
    rectRadius: 0.08,
    line: { color, transparency: 100 },
    fill: { color },
  });
  slide.addText(text, {
    x: x + 0.08,
    y: y + 0.05,
    w: w - 0.16,
    h: 0.18,
    fontFace: "Microsoft YaHei",
    fontSize: 9,
    bold: true,
    align: "center",
    color: textColor,
    margin: 0,
  });
}

function addPanel(slide, x, y, w, h, title = "", opts = {}) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    line: { color: opts.lineColor || C.line, width: 1 },
    fill: { color: opts.fillColor || C.panel },
  });
  if (title) {
    slide.addText(title, {
      x: x + 0.16,
      y: y + 0.12,
      w: w - 0.32,
      h: 0.22,
      fontFace: "Microsoft YaHei",
      fontSize: 11,
      bold: true,
      color: opts.titleColor || C.navy,
      margin: 0,
    });
  }
}

function addBodyText(slide, text, x, y, w, h, opts = {}) {
  const fontFace = opts.fontFace || "Microsoft YaHei";
  const minFont = opts.minFontSize || 10;
  const maxFont = opts.maxFontSize || 18;
  const fitted = autoFontSize(text, fontFace, {
    x,
    y,
    w,
    h,
    fontSize: maxFont,
    minFontSize: minFont,
    maxFontSize: maxFont,
    mode: "shrink",
    margin: 0,
    padding: 0.04,
    leading: opts.leading || 1.28,
  });
  slide.addText(text, {
    x,
    y,
    w,
    h,
    fontFace,
    fontSize: fitted.fontSize,
    color: opts.color || C.text,
    bold: opts.bold || false,
    margin: 0,
    valign: opts.valign || "top",
    align: opts.align || "left",
    breakLine: false,
  });
}

function addBulletList(slide, items, x, y, w, opts = {}) {
  const rowH = opts.rowH || 0.44;
  const bulletColor = opts.bulletColor || C.blue;
  const textColor = opts.textColor || C.text;
  const fontSize = opts.fontSize || 13;
  items.forEach((item, index) => {
    const top = y + index * rowH;
    slide.addShape(pptx.ShapeType.ellipse, {
      x,
      y: top + 0.08,
      w: 0.1,
      h: 0.1,
      line: { color: bulletColor, transparency: 100 },
      fill: { color: bulletColor },
    });
    addBodyText(slide, item, x + 0.18, top, w - 0.18, rowH - 0.02, {
      minFontSize: fontSize,
      maxFontSize: fontSize,
      color: textColor,
      leading: 1.18,
    });
  });
}

function addMetricCard(slide, x, y, w, h, value, label, accent) {
  addPanel(slide, x, y, w, h, "", { fillColor: C.panel2, lineColor: C.line });
  slide.addShape(pptx.ShapeType.rect, {
    x: x,
    y,
    w: 0.08,
    h,
    line: { color: accent, transparency: 100 },
    fill: { color: accent },
  });
  slide.addText(value, {
    x: x + 0.18,
    y: y + 0.15,
    w: w - 0.32,
    h: 0.4,
    fontFace: "Microsoft YaHei",
    fontSize: 22,
    bold: true,
    color: C.text,
    margin: 0,
  });
  slide.addText(label, {
    x: x + 0.18,
    y: y + 0.62,
    w: w - 0.28,
    h: 0.2,
    fontFace: "Microsoft YaHei",
    fontSize: 10,
    color: C.subtext,
    margin: 0,
  });
}

function addStepFlow(slide, steps, x, y, w, colors) {
  const gap = 0.16;
  const boxW = (w - gap * (steps.length - 1)) / steps.length;
  steps.forEach((step, index) => {
    const left = x + index * (boxW + gap);
    addPanel(slide, left, y, boxW, 0.86, "", {
      fillColor: index % 2 === 0 ? C.panel : C.panel2,
      lineColor: C.line,
    });
    slide.addShape(pptx.ShapeType.ellipse, {
      x: left + 0.14,
      y: y + 0.16,
      w: 0.28,
      h: 0.28,
      line: { color: colors[index] || C.blue, transparency: 100 },
      fill: { color: colors[index] || C.blue },
    });
    slide.addText(String(index + 1), {
      x: left + 0.14,
      y: y + 0.21,
      w: 0.28,
      h: 0.1,
      align: "center",
      fontFace: "Microsoft YaHei",
      fontSize: 9,
      bold: true,
      color: C.white,
      margin: 0,
    });
    addBodyText(slide, step, left + 0.5, y + 0.13, boxW - 0.62, 0.56, {
      minFontSize: 10.5,
      maxFontSize: 10.5,
      leading: 1.15,
    });
    if (index < steps.length - 1) {
      slide.addShape(pptx.ShapeType.line, {
        x: left + boxW,
        y: y + 0.43,
        w: gap,
        h: 0,
        line: { color: C.blue, width: 1.5 },
      });
    }
  });
}

function addStepStack(slide, steps, x, y, w, h, colors) {
  const gap = 0.12;
  const boxH = (h - gap * (steps.length - 1)) / steps.length;
  steps.forEach((step, index) => {
    const top = y + index * (boxH + gap);
    addPanel(slide, x, top, w, boxH, "", {
      fillColor: index % 2 === 0 ? C.panel : C.panel2,
      lineColor: C.line,
    });
    slide.addShape(pptx.ShapeType.ellipse, {
      x: x + 0.12,
      y: top + 0.11,
      w: 0.24,
      h: 0.24,
      line: { color: colors[index] || C.blue, transparency: 100 },
      fill: { color: colors[index] || C.blue },
    });
    slide.addText(String(index + 1), {
      x: x + 0.12,
      y: top + 0.16,
      w: 0.24,
      h: 0.1,
      align: "center",
      fontFace: "Microsoft YaHei",
      fontSize: 8.5,
      bold: true,
      color: C.white,
      margin: 0,
    });
    addBodyText(slide, step, x + 0.45, top + 0.08, w - 0.58, boxH - 0.16, {
      minFontSize: 9.2,
      maxFontSize: 9.6,
      leading: 1.14,
    });
  });
}

function stageIcon(label, fill, subFill = "FFFFFF") {
  return svgToDataUri(`
    <svg width="120" height="120" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
      <circle cx="60" cy="60" r="56" fill="#${fill}" opacity="0.16"/>
      <circle cx="60" cy="60" r="42" fill="#${fill}"/>
      <circle cx="60" cy="60" r="28" fill="#${subFill}" opacity="0.18"/>
      <text x="60" y="69" text-anchor="middle" font-family="Microsoft YaHei" font-size="30" font-weight="700" fill="#FFFFFF">${label}</text>
    </svg>
  `);
}

function addIconCard(slide, x, y, w, h, iconText, title, body, color) {
  addPanel(slide, x, y, w, h, "", { fillColor: C.white, lineColor: C.line });
  slide.addImage({
    data: stageIcon(iconText, color),
    x: x + 0.18,
    y: y + 0.14,
    w: 0.62,
    h: 0.62,
  });
  slide.addText(title, {
    x: x + 0.92,
    y: y + 0.18,
    w: w - 1.08,
    h: 0.22,
    fontFace: "Microsoft YaHei",
    fontSize: 11.5,
    bold: true,
    color: C.text,
    margin: 0,
  });
  addBodyText(slide, body, x + 0.18, y + 0.88, w - 0.36, h - 1.02, {
    minFontSize: 9.8,
    maxFontSize: 10.2,
    color: C.subtext,
    leading: 1.22,
  });
}

function addProgressRow(slide, label, percent, note, y, color) {
  slide.addText(label, {
    x: 0.92,
    y,
    w: 2.35,
    h: 0.18,
    fontFace: "Microsoft YaHei",
    fontSize: 11,
    bold: true,
    color: C.text,
    margin: 0,
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 3.05,
    y: y + 0.02,
    w: 4.2,
    h: 0.16,
    rectRadius: 0.05,
    line: { color: C.line, transparency: 100 },
    fill: { color: "E8EDF7" },
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 3.05,
    y: y + 0.02,
    w: 4.2 * (percent / 100),
    h: 0.16,
    rectRadius: 0.05,
    line: { color, transparency: 100 },
    fill: { color },
  });
  slide.addText(`${percent}%`, {
    x: 7.4,
    y: y - 0.01,
    w: 0.7,
    h: 0.2,
    align: "right",
    fontFace: "Microsoft YaHei",
    fontSize: 10.5,
    bold: true,
    color,
    margin: 0,
  });
  addBodyText(slide, note, 8.35, y - 0.02, 3.6, 0.22, {
    minFontSize: 9.6,
    maxFontSize: 9.6,
    color: C.subtext,
  });
}

function finalizeSlide(slide, index, dark = false) {
  if (dark) {
    slide.addText("毕业设计中期检查", {
      x: M,
      y: SH - 0.35,
      w: 2.3,
      h: 0.16,
      fontFace: "Microsoft YaHei",
      fontSize: 8.5,
      color: "D6E4FF",
      margin: 0,
    });
    slide.addText(String(index), {
      x: SW - 0.8,
      y: SH - 0.36,
      w: 0.28,
      h: 0.18,
      align: "right",
      fontFace: "Microsoft YaHei",
      fontSize: 9,
      bold: true,
      color: C.white,
      margin: 0,
    });
  } else {
    addFooter(slide, index);
  }
  if (process.env.SLIDE_VALIDATE === "1") {
    warnIfSlideHasOverlaps(slide, pptx, {
      muteContainment: true,
      ignoreDecorativeShapes: true,
      ignoreLines: true,
    });
    warnIfSlideElementsOutOfBounds(slide, pptx);
  }
}

function addCover() {
  const slide = pptx.addSlide();
  addBg(slide, true);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.72,
    y: 0.9,
    w: 0.92,
    h: 0.34,
    rectRadius: 0.06,
    line: { color: C.cyan, transparency: 100 },
    fill: { color: C.cyan },
  });
  slide.addText("中期检查汇报", {
    x: 0.86,
    y: 0.98,
    w: 0.64,
    h: 0.16,
    align: "center",
    fontFace: "Microsoft YaHei",
    fontSize: 9.5,
    bold: true,
    color: C.white,
    margin: 0,
  });
  slide.addText("基于视觉分析的标准操作流程（SOP）管理系统设计与实现", {
    x: 0.72,
    y: 1.42,
    w: 7.35,
    h: 1.02,
    fontFace: "Microsoft YaHei",
    fontSize: 27,
    bold: true,
    color: C.white,
    margin: 0,
    valign: "mid",
  });
  slide.addText(
    "围绕“标准流程定义—视频执行采集—多模态智能评测—结果复核与统计分析”构建可运行的完整系统闭环",
    {
      x: 0.74,
      y: 2.62,
      w: 6.9,
      h: 0.45,
      fontFace: "Microsoft YaHei",
      fontSize: 12.5,
      color: "D6E4FF",
      margin: 0,
      breakLine: false,
    }
  );
  addMetricCard(slide, 0.76, 3.35, 1.8, 1.05, "75%", "整体完成进度", C.cyan);
  addMetricCard(slide, 2.72, 3.35, 1.8, 1.05, "22页", "汇报内容规模", C.green);
  addMetricCard(slide, 4.68, 3.35, 1.95, 1.05, "前后端闭环", "阶段成果状态", C.amber);

  addPanel(slide, 8.45, 1.05, 4.1, 4.55, "", {
    fillColor: "15305F",
    lineColor: "31538E",
  });
  slide.addText("项目关键词", {
    x: 8.72,
    y: 1.28,
    w: 1.2,
    h: 0.18,
    fontFace: "Microsoft YaHei",
    fontSize: 10,
    bold: true,
    color: "D6E4FF",
    margin: 0,
  });
  [
    ["Vue 3 + FastAPI", C.cyan],
    ["MySQL + OpenCV", C.green],
    ["多模态视频理解", C.amber],
    ["异步评测任务", C.blue],
    ["人工复核与统计", "7B8CFF"],
  ].forEach((item, index) => {
    addPill(slide, item[0], 8.72, 1.62 + index * 0.52, 2.4, item[1]);
  });
  addBodyText(
    slide,
    "项目已经完成主体架构搭建与核心业务联调，当前重点转入评测稳定性、时序识别精度、场景泛化能力以及结果解释性优化。",
    8.72,
    4.42,
    3.4,
    0.84,
    { minFontSize: 11, maxFontSize: 11, color: C.white, leading: 1.26 }
  );
  slide.addText("汇报人：XXX    专业：XXX    指导教师：XXX", {
    x: 0.76,
    y: 6.35,
    w: 5.0,
    h: 0.18,
    fontFace: "Microsoft YaHei",
    fontSize: 10,
    color: "D6E4FF",
    margin: 0,
  });
  finalizeSlide(slide, 1, true);
}

function addAgenda() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "汇报目录", "围绕背景、方案、实现进度、存在问题和后续计划展开。");
  const items = [
    "1 课题背景与研究目标",
    "2 系统需求与总体设计",
    "3 核心功能实现与阶段成果",
    "4 项目进度与当前存在的问题",
    "5 改进措施与下一步计划",
  ];
  items.forEach((item, index) => {
    const y = 1.55 + index * 0.9;
    addPanel(slide, 1.0, y, 10.9, 0.62, "", {
      fillColor: index % 2 === 0 ? C.panel : C.panel2,
    });
    slide.addShape(pptx.ShapeType.ellipse, {
      x: 1.2,
      y: y + 0.13,
      w: 0.32,
      h: 0.32,
      line: { color: C.blue, transparency: 100 },
      fill: { color: C.blue },
    });
    slide.addText(String(index + 1), {
      x: 1.2,
      y: y + 0.18,
      w: 0.32,
      h: 0.1,
      align: "center",
      fontFace: "Microsoft YaHei",
      fontSize: 9.5,
      bold: true,
      color: C.white,
      margin: 0,
    });
    slide.addText(item, {
      x: 1.72,
      y: y + 0.15,
      w: 4.4,
      h: 0.16,
      fontFace: "Microsoft YaHei",
      fontSize: 14.5,
      bold: true,
      color: C.text,
      margin: 0,
    });
  });
  finalizeSlide(slide, 2);
}

function addBackgroundSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "课题背景与研究意义", "以标准流程执行监督为切入点，探索多模态视频理解在规范化管理中的应用。");
  addIconCard(slide, 0.9, 1.45, 3.8, 1.75, "背", "应用背景", "在实验操作、设备巡检、医疗护理等场景中，SOP 是保障质量与安全的关键依据，但实际执行监管仍以人工观察为主。", C.blue);
  addIconCard(slide, 4.9, 1.45, 3.8, 1.75, "痛", "现实痛点", "人工考核效率低、主观性强、难以持续留痕；视频虽然能记录过程，但缺乏结构化分析能力，难以直接支撑评价。", C.amber);
  addIconCard(slide, 8.9, 1.45, 3.5, 1.75, "义", "研究意义", "将 SOP 管理、视频分析与智能评测结合起来，可提升流程监督效率，增强结果的规范性、可追溯性与可复核性。", C.green);
  addPanel(slide, 0.9, 3.55, 11.45, 2.25, "本课题试图解决的核心问题");
  addStepFlow(
    slide,
    [
      "如何把抽象的 SOP 文本描述转换为可执行、可管理、可评测的标准流程对象",
      "如何利用示范视频与执行视频构建统一参考，实现步骤级别的自动判定",
      "如何在给出总分的同时输出问题类型、证据说明和后续整改建议",
    ],
    1.15,
    4.15,
    10.95,
    [C.blue, C.green, C.amber]
  );
  finalizeSlide(slide, 3);
}

function addGoalsSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "研究目标与主要研究内容", "从系统建设视角拆解为管理端、执行端、评测端和数据端四个方面。");
  addPanel(slide, 0.9, 1.45, 5.75, 2.35, "总体目标");
  addBulletList(slide, [
    "设计并实现一个面向 SOP 场景的视频化管理与评测系统",
    "实现“标准流程制定—执行视频上传—智能评测—人工复核”的业务闭环",
    "验证多模态模型在流程执行规范性判断中的可行性与应用价值",
  ], 1.15, 1.92, 5.2, { rowH: 0.52, fontSize: 12.5 });
  addPanel(slide, 6.9, 1.45, 5.45, 2.35, "主要研究内容");
  addBulletList(slide, [
    "SOP 数据结构设计与管理端功能实现",
    "示范视频预处理与步骤参考信息生成",
    "多阶段视频评测流程设计与结果后处理",
    "执行记录、统计分析与人工复核机制实现",
  ], 7.15, 1.92, 4.9, { rowH: 0.45, fontSize: 12 });

  addPanel(slide, 0.9, 4.15, 11.45, 1.55, "功能目标拆解");
  [
    ["管理端", "SOP 创建、步骤配置、示范视频上传、AI 参数配置", C.blue],
    ["执行端", "查看任务、上传视频、获取评测结果与历史记录", C.green],
    ["评测端", "时序分析、分步评测、顺序校验、规则后处理", C.amber],
    ["数据端", "结果存储、问题统计、人工复核与过程可解释展示", C.teal],
  ].forEach((item, index) => {
    const x = 1.15 + index * 2.77;
    addPanel(slide, x, 4.55, 2.42, 0.86, "", { fillColor: C.panel2 });
    addPill(slide, item[0], x + 0.12, 4.67, 0.82, item[2]);
    addBodyText(slide, item[1], x + 0.12, 5.02, 2.12, 0.24, {
      minFontSize: 9.4,
      maxFontSize: 9.4,
      color: C.subtext,
      leading: 1.15,
    });
  });
  finalizeSlide(slide, 5);
}

function addRequirementsSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "系统需求分析", "系统面向管理员和普通用户两类角色，不同角色承担不同业务职责。");
  addPanel(slide, 0.9, 1.45, 5.45, 3.75, "管理员需求");
  addBulletList(slide, [
    "创建 SOP，定义步骤描述、步骤类型、步骤权重和前置依赖",
    "上传完整示范视频，生成参考帧、关键时刻和 ROI 提示",
    "查看执行记录，对 AI 评测结果进行人工复核",
    "查看统计分析结果，并维护用户与模型配置",
  ], 1.15, 1.95, 4.95, { rowH: 0.58, fontSize: 12.2, bulletColor: C.blue });
  addPanel(slide, 6.7, 1.45, 5.65, 3.75, "普通用户需求");
  addBulletList(slide, [
    "登录系统并浏览待执行 SOP 任务列表",
    "查看流程步骤说明和参考信息，上传完整执行视频",
    "跟踪异步评测进度，查看得分、问题标签和证据说明",
    "查看个人历史记录与人工复核结论",
  ], 6.95, 1.95, 5.05, { rowH: 0.58, fontSize: 12.2, bulletColor: C.green });
  addPanel(slide, 0.9, 5.45, 11.45, 1.1, "系统非功能需求");
  addStepFlow(
    slide,
    [
      "支持长视频异步评测，避免阻塞交互流程",
      "结果需要可留痕、可追溯、可复核",
      "前后端分离，便于后续拓展和维护",
      "支持结构化输出，便于统计分析",
    ],
    1.1,
    5.8,
    11.05,
    [C.blue, C.amber, C.teal, C.green]
  );
  finalizeSlide(slide, 6);
}

function addTechRouteSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "总体技术路线", "采用“前端交互 + 后端服务 + 视频处理 + 多模态评测 + 数据留痕”的组合方案。");
  addStepFlow(
    slide,
    [
      "Vue 3 / Element Plus\n构建管理端与用户端交互界面",
      "FastAPI / MySQL\n提供 API、鉴权与业务数据存储",
      "OpenCV / FFmpeg\n完成视频读写、抽帧与格式处理",
      "多模态大模型\n执行时序分析、分步判断与全局校验",
      "历史记录与统计\n沉淀评测结果并支撑复核分析",
    ],
    0.9,
    1.75,
    11.55,
    [C.blue, C.teal, C.green, C.amber, C.navy]
  );

  addPanel(slide, 0.9, 3.25, 11.45, 2.4, "关键设计思路");
  addBulletList(slide, [
    "不要求用户逐步上传视频，而是采用完整执行视频一次性上传，降低使用门槛。",
    "管理员上传整段示范视频后，由系统自动为各步骤生成参考信息，减少人工维护成本。",
    "评测链路采用多阶段设计：先做时序定位，再做分步判断，最后进行全局顺序校验。",
    "在模型输出基础上叠加规则后处理，兼顾模型灵活性与流程约束的确定性。",
  ], 1.15, 3.7, 10.95, { rowH: 0.48, fontSize: 11.5 });
  finalizeSlide(slide, 7);
}

function addArchitectureSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "系统总体架构设计", "系统采用前后端分离结构，异步 Worker 负责耗时评测任务。");
  addPanel(slide, 0.95, 1.55, 2.5, 1.08, "前端展示层", { fillColor: "EFF5FF" });
  addBodyText(slide, "Vue 3 + Vue Router + Element Plus\n管理员端 / 用户端 / 结果展示", 1.15, 1.97, 2.08, 0.48, {
    minFontSize: 11,
    maxFontSize: 11,
    color: C.subtext,
  });
  addPanel(slide, 4.02, 1.55, 2.75, 1.08, "后端接口层", { fillColor: "F4FBFF" });
  addBodyText(slide, "FastAPI + Pydantic\n鉴权、SOP 管理、历史查询、任务接口", 4.22, 1.97, 2.3, 0.48, {
    minFontSize: 11,
    maxFontSize: 11,
    color: C.subtext,
  });
  addPanel(slide, 7.35, 1.55, 2.75, 1.08, "任务处理层", { fillColor: "F5FFF8" });
  addBodyText(slide, "Evaluation Worker\n异步轮询、日志记录、评测状态更新", 7.55, 1.97, 2.3, 0.48, {
    minFontSize: 11,
    maxFontSize: 11,
    color: C.subtext,
  });
  addPanel(slide, 10.68, 1.55, 1.7, 1.08, "模型服务", { fillColor: "FFF8EE" });
  addBodyText(slide, "OpenAI 兼容\n多模态大模型", 10.88, 1.97, 1.3, 0.42, {
    minFontSize: 10.5,
    maxFontSize: 10.5,
    color: C.subtext,
  });
  [
    [3.45, 2.08, 0.55],
    [6.78, 2.08, 0.55],
    [10.11, 2.08, 0.55],
  ].forEach((line) => {
    slide.addShape(pptx.ShapeType.line, {
      x: line[0],
      y: line[1],
      w: line[2],
      h: 0,
      line: { color: C.blue, width: 1.6 },
    });
  });
  addPanel(slide, 1.25, 3.15, 4.7, 2.15, "数据与文件层");
  addBulletList(slide, [
    "MySQL：用户、SOP、任务、历史、统计数据",
    "媒体文件：示范视频、执行视频、关键帧",
    "结构化结果：步骤得分、问题类型、证据文本",
  ], 1.48, 3.63, 4.18, { rowH: 0.5, fontSize: 11.2, bulletColor: C.navy });
  addPanel(slide, 6.25, 3.15, 5.45, 2.15, "能力支撑层");
  addBulletList(slide, [
    "OpenCV / FFmpeg：视频读写、抽帧、格式标准化",
    "httpx：调用多模态模型接口",
    "规则评分模块：步骤权重、条件步骤、前置依赖、问题扣分",
  ], 6.48, 3.63, 4.9, { rowH: 0.5, fontSize: 11.2, bulletColor: C.teal });
  finalizeSlide(slide, 7);
}

function addFlowSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "关键业务流程设计", "围绕管理员建模、用户执行与系统评测形成闭环流程。");
  addPanel(slide, 0.9, 1.5, 2.75, 4.5, "管理员侧");
  addStepStack(slide, [
    "创建 SOP",
    "配置步骤信息",
    "上传示范视频",
    "生成参考信息",
  ], 1.12, 2.0, 2.3, 3.55, [C.blue, C.blue, C.blue, C.blue]);
  addPanel(slide, 3.95, 1.5, 4.1, 4.5, "系统处理侧");
  addStepStack(slide, [
    "创建评测任务",
    "时序分割",
    "分步评测",
    "全局校验",
    "规则后处理",
    "保存结果",
  ], 4.18, 2.0, 3.64, 3.62, [C.amber, C.amber, C.amber, C.amber, C.amber, C.amber]);
  addPanel(slide, 8.35, 1.5, 4.0, 4.5, "用户侧");
  addStepStack(slide, [
    "查看 SOP",
    "上传执行视频",
    "轮询任务进度",
    "查看评测结果",
    "查看历史与复核",
  ], 8.58, 2.0, 3.54, 3.58, [C.green, C.green, C.green, C.green, C.green]);
  finalizeSlide(slide, 8);
}

function addProgressSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "项目进度总览", "当前已完成系统主体功能实现，整体进度可表述为约 75%。");
  addMetricCard(slide, 0.95, 1.48, 2.1, 1.05, "75%", "整体完成度", C.blue);
  addMetricCard(slide, 3.28, 1.48, 2.3, 1.05, "主体已打通", "当前阶段状态", C.green);
  addMetricCard(slide, 5.82, 1.48, 2.1, 1.05, "多阶段评测", "核心链路", C.amber);
  addMetricCard(slide, 8.16, 1.48, 3.2, 1.05, "优化与完善阶段", "后续工作重心", C.teal);

  addPanel(slide, 0.95, 2.95, 11.2, 3.05, "分模块进度");
  addProgressRow(slide, "需求分析与总体方案设计", 100, "已完成", 3.45, C.green);
  addProgressRow(slide, "前后端基础框架搭建", 100, "已完成", 3.88, C.green);
  addProgressRow(slide, "登录权限与角色管理模块", 100, "已完成", 4.31, C.green);
  addProgressRow(slide, "SOP 管理与数据库设计", 90, "基本完成", 4.74, C.blue);
  addProgressRow(slide, "示范视频预处理与参考信息生成", 85, "基本完成", 5.17, C.blue);
  addProgressRow(slide, "多阶段 AI 视频评测流程", 85, "基本完成", 5.60, C.amber);
  addProgressRow(slide, "历史记录、统计与人工复核", 90, "基本完成", 6.03, C.blue);
  finalizeSlide(slide, 9);
}

function addAuthSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "核心功能实现（一）用户与权限管理", "实现系统基础访问控制，为后续业务功能提供角色隔离。");
  addPanel(slide, 0.95, 1.52, 5.2, 4.3, "已实现内容");
  addBulletList(slide, [
    "登录、注册、退出以及当前用户信息查询",
    "管理员与普通用户角色区分，不同角色进入不同工作台",
    "支持用户启用 / 禁用，限制异常账户继续使用系统",
    "基于 Token 和会话信息进行访问控制与状态同步",
  ], 1.18, 2.02, 4.7, { rowH: 0.58, fontSize: 12.2, bulletColor: C.blue });
  addPanel(slide, 6.45, 1.52, 5.7, 4.3, "实现效果");
  addStepFlow(
    slide,
    [
      "未登录状态访问系统",
      "输入账号密码完成认证",
      "根据角色自动跳转到管理员端或用户端",
      "后续接口访问均带鉴权信息",
    ],
    6.68,
    2.18,
    5.24,
    [C.green, C.green, C.green, C.green]
  );
  finalizeSlide(slide, 10);
}

function addSopSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "核心功能实现（二）SOP 建模与管理", "管理员端已能完成 SOP 从定义到发布的主要建模工作。");
  addPanel(slide, 0.95, 1.5, 4.2, 4.55, "SOP 建模要素");
  addBulletList(slide, [
    "SOP 名称、场景、步骤数量等基础信息",
    "步骤描述、步骤类型（必选 / 可选 / 条件）",
    "步骤权重、条件触发说明、前置依赖关系",
    "自定义问题类型扣分参数配置",
  ], 1.18, 2.0, 3.72, { rowH: 0.62, fontSize: 12.1, bulletColor: C.blue });
  addPanel(slide, 5.45, 1.5, 6.7, 4.55, "功能状态");
  [
    ["查看 SOP 列表", "已实现", C.green],
    ["新建 SOP", "已实现", C.green],
    ["删除 SOP 及关联媒体", "已实现", C.green],
    ["步骤级示范视频替换", "已实现", C.blue],
    ["步骤参考信息手动修正", "已实现", C.blue],
  ].forEach((item, index) => {
    const y = 1.85 + index * 0.66;
    addPanel(slide, 5.72, y, 6.12, 0.46, "", {
      fillColor: index % 2 === 0 ? C.panel : C.panel2,
    });
    slide.addText(item[0], {
      x: 5.92,
      y: y + 0.12,
      w: 2.8,
      h: 0.16,
      fontFace: "Microsoft YaHei",
      fontSize: 11.4,
      color: C.text,
      margin: 0,
    });
    addPill(slide, item[1], 10.58, y + 0.07, 0.92, item[2]);
  });
  finalizeSlide(slide, 12);
}

function addPreprocessSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "核心功能实现（三）示范视频预处理", "管理员上传完整流程视频后，系统自动提取步骤级参考信息。");
  addPanel(slide, 0.95, 1.48, 11.2, 1.0, "设计思路");
  addBodyText(slide, "不要求管理员为每一个步骤单独上传短视频，而是上传一段完整流程示范视频；系统依据步骤描述与时序分析结果自动生成步骤级参考包。", 1.2, 1.83, 10.7, 0.4, {
    minFontSize: 11.2,
    maxFontSize: 11.2,
    color: C.subtext,
  });
  addStepFlow(
    slide,
    [
      "读取整段示范视频",
      "识别各步骤大致时间范围",
      "抽取关键帧与分析帧",
      "生成参考摘要、关键时刻和 ROI 提示",
      "写入 SOP 步骤参考信息",
    ],
    0.95,
    2.9,
    11.2,
    [C.blue, C.teal, C.green, C.amber, C.navy]
  );
  addPanel(slide, 0.95, 4.35, 5.4, 1.5, "当前实现价值");
  addBulletList(slide, [
    "降低管理员维护成本",
    "为后续分步评测提供视觉参考",
    "支持手动覆盖和关键时刻修正",
  ], 1.18, 4.75, 4.9, { rowH: 0.32, fontSize: 10.8, bulletColor: C.green });
  addPanel(slide, 6.7, 4.35, 5.45, 1.5, "当前局限");
  addBulletList(slide, [
    "步骤边界不明显时，自动切分结果仍可能偏粗",
    "复杂动作的 ROI 提取质量受示范视频质量影响较大",
    "后续仍需增强自动切分与人工校正结合能力",
  ], 6.93, 4.72, 4.92, { rowH: 0.32, fontSize: 10.6, bulletColor: C.amber });
  finalizeSlide(slide, 12);
}

function addEvalSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "核心功能实现（四）多阶段 AI 视频评测", "系统已形成面向执行视频的三阶段评测链路。");
  addStepFlow(
    slide,
    [
      "阶段一：时序分割\n定位各步骤在用户视频中的候选区间",
      "阶段二：分步评测\n逐步判断动作完成情况、得分与证据",
      "阶段三：全局校验\n综合检查顺序依赖与整体合理性",
    ],
    0.95,
    1.75,
    11.2,
    [C.blue, C.green, C.amber]
  );
  addPanel(slide, 0.95, 3.2, 5.35, 2.45, "模型输出内容");
  addBulletList(slide, [
    "是否通过（passed）",
    "综合得分（score）",
    "综合反馈（feedback）",
    "问题标签列表（issues）",
    "步骤级结果（stepResults）与证据说明",
  ], 1.18, 3.66, 4.9, { rowH: 0.38, fontSize: 11.1, bulletColor: C.blue });
  addPanel(slide, 6.62, 3.2, 5.53, 2.45, "后处理规则");
  addBulletList(slide, [
    "结合步骤权重重新计算综合分",
    "对条件步骤和可选步骤进行适用性判断",
    "检查前置依赖是否被违反",
    "根据问题类型实施差异化扣分",
    "给出最终通过 / 未通过结论",
  ], 6.85, 3.66, 5.02, { rowH: 0.38, fontSize: 11.1, bulletColor: C.green });
  finalizeSlide(slide, 13);
}

function addAsyncSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "核心功能实现（五）异步任务、历史记录与结果闭环", "针对视频评测耗时较长的特点，引入任务队列与历史留痕机制。");
  addPanel(slide, 0.95, 1.52, 11.2, 1.25, "异步任务机制");
  addStepFlow(
    slide,
    [
      "用户上传执行视频",
      "系统创建 evaluation_job",
      "Worker 轮询并处理任务",
      "前端轮询状态与日志",
      "完成后写入历史记录",
    ],
    1.2,
    1.98,
    10.7,
    [C.blue, C.blue, C.amber, C.green, C.teal]
  );
  addPanel(slide, 0.95, 3.15, 5.4, 2.55, "用户端已实现能力");
  addBulletList(slide, [
    "查看待执行 SOP 列表并进入执行页面",
    "上传完整执行视频并提交评测任务",
    "查看任务进度、日志、失败原因与重试状态",
    "查看历史记录中的评测结果和人工复核结论",
  ], 1.18, 3.62, 4.95, { rowH: 0.48, fontSize: 11.5, bulletColor: C.green });
  addPanel(slide, 6.72, 3.15, 5.43, 2.55, "结果展示特点");
  addBulletList(slide, [
    "结果页展示总分、问题标签和步骤级证据",
    "支持时间轴与评测过程展开显示",
    "支持查看 Token 使用与多阶段模型响应摘要",
    "增强评测结果的可解释性与可追溯性",
  ], 6.95, 3.62, 4.95, { rowH: 0.48, fontSize: 11.5, bulletColor: C.teal });
  finalizeSlide(slide, 14);
}

function addStatsSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "核心功能实现（六）统计分析与人工复核", "管理员端不仅能查看结果，还能进行复核与统计分析。");
  addMetricCard(slide, 0.98, 1.55, 2.45, 1.05, "SOP 维度统计", "执行次数 / 通过率 / 平均分", C.blue);
  addMetricCard(slide, 3.67, 1.55, 2.45, 1.05, "问题类型统计", "识别高频异常类型", C.amber);
  addMetricCard(slide, 6.36, 1.55, 2.45, 1.05, "人工复核", "通过 / 不通过 / 需整改", C.green);
  addMetricCard(slide, 9.05, 1.55, 3.1, 1.05, "过程展示", "查看多阶段提示与响应摘要", C.teal);
  addPanel(slide, 0.98, 3.0, 5.45, 2.6, "统计分析价值");
  addBulletList(slide, [
    "从单次结果扩展到 SOP 维度、问题维度和整体维度分析",
    "帮助识别高频异常步骤，为后续教学或培训提供依据",
    "支持管理者从“个体评测”走向“流程优化”",
  ], 1.22, 3.48, 4.95, { rowH: 0.54, fontSize: 11.4, bulletColor: C.blue });
  addPanel(slide, 6.7, 3.0, 5.45, 2.6, "人工复核价值");
  addBulletList(slide, [
    "避免完全依赖模型单次判断，保留人工决策入口",
    "支持对关键记录进行通过 / 不通过 / 需整改处理",
    "形成 AI 判断与人工确认相结合的结果闭环",
  ], 6.94, 3.48, 4.95, { rowH: 0.54, fontSize: 11.4, bulletColor: C.green });
  finalizeSlide(slide, 15);
}

function addDatabaseSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "数据库设计", "数据层围绕“用户—SOP—任务—执行—复核”建立完整关联。");
  const groups = [
    { title: "用户与会话", x: 0.95, items: ["users", "user_login_sessions"], color: C.blue },
    { title: "SOP 定义", x: 3.4, items: ["sops", "sop_steps", "sop_step_prerequisites"], color: C.green },
    { title: "媒体资源", x: 6.28, items: ["media_files", "sop_step_keyframes", "sop_step_substeps"], color: C.amber },
    { title: "评测与结果", x: 9.25, items: ["evaluation_jobs", "sop_executions", "execution_step_results", "manual_reviews"], color: C.teal },
  ];
  groups.forEach((group) => {
    addPanel(slide, group.x, 1.7, 2.3, 3.95, group.title, {
      fillColor: C.panel,
      lineColor: C.line,
    });
    addPill(slide, group.title, group.x + 0.18, 2.02, 0.94, group.color);
    group.items.forEach((item, index) => {
      addPanel(slide, group.x + 0.18, 2.45 + index * 0.68, 1.94, 0.46, "", {
        fillColor: index % 2 === 0 ? C.panel2 : C.white,
      });
      slide.addText(item, {
        x: group.x + 0.3,
        y: 2.58 + index * 0.68,
        w: 1.66,
        h: 0.14,
        fontFace: "Microsoft YaHei",
        fontSize: 10.2,
        color: C.text,
        margin: 0,
        align: "center",
      });
    });
  });
  addPanel(slide, 0.95, 5.92, 11.2, 0.72, "设计特点");
  addBodyText(slide, "数据库设计不仅满足基础业务存储，还保留了任务日志、步骤级结果、问题列表、人工复核等信息，便于后续统计分析与结果追溯。", 1.18, 6.14, 10.7, 0.24, {
    minFontSize: 10.8,
    maxFontSize: 10.8,
    color: C.subtext,
  });
  finalizeSlide(slide, 16);
}

function addHighlightsSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "系统特点与阶段性创新点", "相较于单纯的表单系统或单次模型调用，本项目强调流程闭环与评测可解释性。");
  addIconCard(slide, 0.95, 1.55, 3.65, 1.9, "整", "整段示范视频建模", "管理员上传完整流程视频后，系统自动提取步骤级参考信息，避免逐步维护多个短视频片段。", C.blue);
  addIconCard(slide, 4.85, 1.55, 3.65, 1.9, "多", "多阶段评测链路", "将时序定位、步骤判定和全局顺序校验分离处理，提高复杂流程场景下的分析能力与可控性。", C.green);
  addIconCard(slide, 8.75, 1.55, 3.4, 1.9, "释", "结果可解释展示", "记录步骤证据、过程摘要与任务日志，增强评测结果的可追溯性和人工复核价值。", C.amber);
  addPanel(slide, 0.95, 3.95, 11.2, 1.85, "与传统方式相比的改进");
  addStepFlow(
    slide,
    [
      "从“人工观察 + 主观判断”转向“视频留痕 + 结构化评测”",
      "从“单次打分”转向“任务、步骤、问题类型多维结果沉淀”",
      "从“黑盒结论”转向“可查看过程、证据与复核意见的结果呈现”",
    ],
    1.18,
    4.42,
    10.7,
    [C.blue, C.green, C.amber]
  );
  finalizeSlide(slide, 17);
}

function addResultsSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "阶段性成果总结", "中期阶段已经完成从需求到核心功能落地的主体工作。");
  addPanel(slide, 0.95, 1.55, 5.6, 4.35, "已取得的阶段成果");
  addBulletList(slide, [
    "完成系统总体架构设计与前后端分离实现",
    "实现管理员端、用户端与后端接口的主要业务联调",
    "完成示范视频预处理、多阶段 AI 评测与结果后处理",
    "实现异步任务、历史记录、统计分析和人工复核闭环",
    "后端已具备较完整的回归测试基础，说明核心逻辑已形成稳定框架",
  ], 1.18, 2.05, 5.08, { rowH: 0.56, fontSize: 11.6, bulletColor: C.blue });
  addPanel(slide, 6.88, 1.55, 5.27, 4.35, "中期阶段结论");
  addBodyText(slide, "当前项目已经达到“系统主体可运行、核心流程可演示、关键结果可展示”的中期检查要求。下一阶段重点不再是从零搭建功能，而是围绕评测效果、场景泛化与结果表达继续优化。", 7.15, 2.05, 4.75, 0.92, {
    minFontSize: 12,
    maxFontSize: 12,
    color: C.text,
    leading: 1.28,
  });
  addMetricCard(slide, 7.15, 3.32, 1.35, 0.92, "主体完成", "系统结构", C.green);
  addMetricCard(slide, 8.72, 3.32, 1.55, 0.92, "链路打通", "业务流程", C.blue);
  addMetricCard(slide, 10.48, 3.32, 1.42, 0.92, "待优化", "评测效果", C.amber);
  finalizeSlide(slide, 18);
}

function addProblemsOneSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "当前存在的核心问题（一）", "问题聚焦于评测效果本身，而非边缘工程事项。");
  addPanel(slide, 0.95, 1.55, 5.5, 4.7, "问题 1：评测结果稳定性仍不足");
  addBulletList(slide, [
    "不同拍摄角度、光照、遮挡和清晰度条件下，同一动作的判断结果仍可能波动。",
    "大模型对细微动作和局部差异较敏感，导致评分一致性仍需加强。",
    "当用户视频质量下降时，步骤证据与最终结论的可靠性会受到影响。",
  ], 1.18, 2.08, 5.0, { rowH: 0.62, fontSize: 11.8, bulletColor: C.red, textColor: C.text });
  addPanel(slide, 6.68, 1.55, 5.47, 4.7, "问题 2：复杂时序动作识别难度较高");
  addBulletList(slide, [
    "对于顺序依赖强、持续时间短、步骤衔接紧密的 SOP，步骤定位仍可能偏差。",
    "当多个动作在时间上紧邻出现时，系统难以稳定区分“漏做、错做、先后顺序错误”等情况。",
    "前置依赖判断虽然已接入规则校验，但时序定位误差会继续影响最终判定精度。",
  ], 6.92, 2.08, 4.95, { rowH: 0.62, fontSize: 11.8, bulletColor: C.amber, textColor: C.text });
  finalizeSlide(slide, 19);
}

function addProblemsTwoSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "当前存在的核心问题（二）", "中期阶段的重点不是“有没有功能”，而是“功能效果还能如何提升”。");
  addIconCard(slide, 0.95, 1.55, 3.55, 2.15, "映", "示范视频到标准步骤的映射仍不够精细", "当前主要依赖完整流程视频自动切分生成参考信息，但部分步骤边界不明显，参考帧、关键时刻和 ROI 的质量仍有提升空间。", C.blue);
  addIconCard(slide, 4.78, 1.55, 3.55, 2.15, "泛", "系统场景泛化能力仍有待提升", "目前系统已能覆盖既定场景的 SOP 评测，但当操作对象、拍摄环境或流程类型变化较大时，模型适应性仍需增强。", C.green);
  addIconCard(slide, 8.6, 1.55, 3.55, 2.15, "释", "评测解释性与可复核性仍需加强", "虽然已输出得分、问题类型和证据文本，但“错在哪里、为什么错、如何改进”仍可以做得更直观。", C.amber);
  addPanel(slide, 0.95, 4.15, 11.2, 1.55, "问题归纳");
  addBodyText(slide, "上述问题说明：项目中后期的重点将从“功能搭建”转向“效果优化”。核心任务是继续缩小参考建模与真实执行之间的差距，提升系统在复杂流程和多场景下的评测准确性与可解释性。", 1.18, 4.55, 10.72, 0.62, {
    minFontSize: 11.2,
    maxFontSize: 11.2,
    color: C.subtext,
    leading: 1.28,
  });
  finalizeSlide(slide, 20);
}

function addPlanSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "改进措施与下一步计划", "下一阶段将围绕模型判定效果、参考建模质量和结果表达能力继续推进。");
  addStepFlow(
    slide,
    [
      "优化评测提示词与判定规则",
      "增强时序分析能力",
      "改进参考信息生成方式",
      "扩展多场景样本与 SOP 类型",
      "强化结果展示与反馈能力",
    ],
    0.95,
    1.8,
    11.2,
    [C.blue, C.green, C.amber, C.teal, C.navy]
  );
  addPanel(slide, 0.95, 3.15, 11.2, 2.55, "具体计划");
  addBulletList(slide, [
    "针对易混淆步骤补充更明确的动作描述、顺序约束和异常判定规则，提高评测一致性。",
    "继续优化短时动作、相邻步骤和前置依赖步骤的定位能力，提升复杂 SOP 识别效果。",
    "优化关键帧、关键时刻和 ROI 提取策略，并预留人工微调入口，提高标准参考质量。",
    "增加更多拍摄环境和流程类型样本，逐步验证并提升系统泛化能力。",
    "将评测结果与时间轴、问题片段和改进建议建立更清晰的对应关系，提升可解释性。",
  ], 1.18, 3.58, 10.7, { rowH: 0.44, fontSize: 11.1, bulletColor: C.blue });
  finalizeSlide(slide, 21);
}

function addSummarySlide() {
  const slide = pptx.addSlide();
  addBg(slide, true);
  slide.addText("中期总结", {
    x: 0.8,
    y: 0.82,
    w: 2.2,
    h: 0.36,
    fontFace: "Microsoft YaHei",
    fontSize: 24,
    bold: true,
    color: C.white,
    margin: 0,
  });
  slide.addText(
    "项目已经完成系统主体搭建与核心流程实现，验证了“基于多模态视频理解的 SOP 自动评测”这一思路的可行性。",
    {
      x: 0.82,
      y: 1.45,
      w: 8.6,
      h: 0.62,
      fontFace: "Microsoft YaHei",
      fontSize: 14,
      color: "D7E6FF",
      margin: 0,
      valign: "mid",
    }
  );
  addPanel(slide, 0.82, 2.35, 3.55, 2.2, "", { fillColor: "133160", lineColor: "2F4F87" });
  addPanel(slide, 4.7, 2.35, 3.55, 2.2, "", { fillColor: "133160", lineColor: "2F4F87" });
  addPanel(slide, 8.58, 2.35, 3.75, 2.2, "", { fillColor: "133160", lineColor: "2F4F87" });
  slide.addText("阶段判断", {
    x: 1.02, y: 2.62, w: 0.8, h: 0.16, fontFace: "Microsoft YaHei", fontSize: 10.5, bold: true, color: "8FC6FF", margin: 0,
  });
  slide.addText("系统主体功能已完成", {
    x: 1.02, y: 3.05, w: 2.9, h: 0.3, fontFace: "Microsoft YaHei", fontSize: 18, bold: true, color: C.white, margin: 0,
  });
  slide.addText("已具备中期检查展示条件", {
    x: 1.02, y: 3.52, w: 2.4, h: 0.18, fontFace: "Microsoft YaHei", fontSize: 11, color: "D7E6FF", margin: 0,
  });
  slide.addText("后续重心", {
    x: 4.9, y: 2.62, w: 0.8, h: 0.16, fontFace: "Microsoft YaHei", fontSize: 10.5, bold: true, color: "8FC6FF", margin: 0,
  });
  slide.addText("评测效果持续优化", {
    x: 4.9, y: 3.05, w: 2.9, h: 0.3, fontFace: "Microsoft YaHei", fontSize: 18, bold: true, color: C.white, margin: 0,
  });
  slide.addText("聚焦时序识别、泛化和解释性", {
    x: 4.9, y: 3.52, w: 2.8, h: 0.18, fontFace: "Microsoft YaHei", fontSize: 11, color: "D7E6FF", margin: 0,
  });
  slide.addText("最终目标", {
    x: 8.78, y: 2.62, w: 0.8, h: 0.16, fontFace: "Microsoft YaHei", fontSize: 10.5, bold: true, color: "8FC6FF", margin: 0,
  });
  slide.addText("形成可演示、可答辩、可论文支撑的完整成果", {
    x: 8.78, y: 2.95, w: 3.1, h: 0.5, fontFace: "Microsoft YaHei", fontSize: 16, bold: true, color: C.white, margin: 0, valign: "mid",
  });
  slide.addText("谢谢老师聆听", {
    x: 0.82, y: 6.25, w: 2.4, h: 0.18, fontFace: "Microsoft YaHei", fontSize: 16, bold: true, color: C.white, margin: 0,
  });
  finalizeSlide(slide, 22, true);
}

function addShotPlaceholder(slide, x, y, w, h, title, note = "") {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.06,
    line: { color: "C9D6EA", width: 1.2, dash: "dash" },
    fill: { color: "FAFCFF" },
  });
  slide.addText(title, {
    x: x + 0.18,
    y: y + 0.18,
    w: w - 0.36,
    h: 0.22,
    fontFace: "Microsoft YaHei",
    fontSize: 14,
    bold: true,
    color: C.navy,
    align: "center",
    margin: 0,
  });
  slide.addText("截图占位区", {
    x: x + 0.18,
    y: y + h / 2 - 0.16,
    w: w - 0.36,
    h: 0.22,
    fontFace: "Microsoft YaHei",
    fontSize: 18,
    bold: true,
    color: "9AA9BE",
    align: "center",
    margin: 0,
  });
  if (note) {
    slide.addText(note, {
      x: x + 0.18,
      y: y + h - 0.38,
      w: w - 0.36,
      h: 0.16,
      fontFace: "Microsoft YaHei",
      fontSize: 10,
      color: C.subtext,
      align: "center",
      margin: 0,
    });
  }
}

function addSimpleRow(slide, x, y, w, h, left, right, fillColor = "FFFFFF") {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.03,
    line: { color: C.line, width: 1 },
    fill: { color: fillColor },
  });
  slide.addText(left, {
    x: x + 0.14,
    y: y + 0.1,
    w: w * 0.34,
    h: h - 0.12,
    fontFace: "Microsoft YaHei",
    fontSize: 10.5,
    bold: true,
    color: C.text,
    margin: 0,
    valign: "mid",
  });
  addBodyText(slide, right, x + w * 0.36, y + 0.08, w * 0.6, h - 0.12, {
    minFontSize: 9.3,
    maxFontSize: 9.8,
    color: C.subtext,
    leading: 1.15,
  });
}

function addFlowNode(slide, x, y, w, h, title, body, color = C.blue) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.05,
    line: { color: "D6E0F3", width: 1 },
    fill: { color: "F8FBFF" },
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: x + 0.14,
    y: y + 0.12,
    w: 0.8,
    h: 0.26,
    rectRadius: 0.04,
    line: { color, transparency: 100 },
    fill: { color },
  });
  slide.addText(title, {
    x: x + 0.22,
    y: y + 0.18,
    w: 0.64,
    h: 0.1,
    fontFace: "Microsoft YaHei",
    fontSize: 8.8,
    bold: true,
    align: "center",
    color: C.white,
    margin: 0,
  });
  addBodyText(slide, body, x + 0.16, y + 0.5, w - 0.32, h - 0.62, {
    minFontSize: 9.6,
    maxFontSize: 10,
    color: C.subtext,
    leading: 1.15,
  });
}

function addArrow(slide, x, y, w, color = C.blue) {
  slide.addShape(pptx.ShapeType.line, {
    x,
    y,
    w,
    h: 0,
    line: { color, width: 1.4, beginArrowType: "none", endArrowType: "triangle" },
  });
}

function addStatusTag(slide, text, x, y, w, color) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 0.27,
    rectRadius: 0.04,
    line: { color, transparency: 100 },
    fill: { color },
  });
  slide.addText(text, {
    x,
    y: y + 0.065,
    w,
    h: 0.1,
    fontFace: "Microsoft YaHei",
    fontSize: 8.4,
    bold: true,
    align: "center",
    color: C.white,
    margin: 0,
  });
}

function addModuleStatusCard(slide, x, y, w, h, title, items, status, color, fillColor) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.06,
    line: { color: "D8E2F1", width: 1 },
    fill: { color: fillColor },
  });
  slide.addShape(pptx.ShapeType.line, {
    x: x + 0.18,
    y: y + 0.38,
    w: w - 0.36,
    h: 0,
    line: { color, width: 1.5 },
  });
  slide.addText(title, {
    x: x + 0.18,
    y: y + 0.14,
    w: w - 1.25,
    h: 0.2,
    fontFace: "Microsoft YaHei",
    fontSize: 11.6,
    bold: true,
    color: C.text,
    margin: 0,
  });
  addStatusTag(slide, status, x + w - 1.02, y + 0.11, 0.84, color);
  items.forEach((item, index) => {
    const rowY = y + 0.55 + index * 0.24;
    slide.addShape(pptx.ShapeType.ellipse, {
      x: x + 0.2,
      y: rowY + 0.055,
      w: 0.06,
      h: 0.06,
      line: { color, transparency: 100 },
      fill: { color },
    });
    slide.addText(item, {
      x: x + 0.34,
      y: rowY,
      w: w - 0.5,
      h: 0.12,
      fontFace: "Microsoft YaHei",
      fontSize: 9.2,
      color: C.subtext,
      margin: 0,
    });
  });
}

function addMinimalCover() {
  const slide = pptx.addSlide();
  addBg(slide);
  slide.addText("基于视觉分析的标准操作流程（SOP）管理系统设计与实现", {
    x: 0.9,
    y: 1.45,
    w: 8.8,
    h: 1.0,
    fontFace: "Microsoft YaHei",
    fontSize: 25,
    bold: true,
    color: C.text,
    margin: 0,
    valign: "mid",
  });
  slide.addShape(pptx.ShapeType.line, {
    x: 0.92,
    y: 2.72,
    w: 3.5,
    h: 0,
    line: { color: C.blue, width: 2 },
  });
  slide.addText("汇报人：XXX", {
    x: 0.92,
    y: 3.3,
    w: 2.2,
    h: 0.22,
    fontFace: "Microsoft YaHei",
    fontSize: 16,
    color: C.text,
    margin: 0,
  });
  slide.addText("班级：XXX", {
    x: 0.92,
    y: 3.78,
    w: 2.2,
    h: 0.22,
    fontFace: "Microsoft YaHei",
    fontSize: 16,
    color: C.text,
    margin: 0,
  });
  slide.addText("日期：2026-04-12", {
    x: 0.92,
    y: 4.26,
    w: 2.8,
    h: 0.22,
    fontFace: "Microsoft YaHei",
    fontSize: 16,
    color: C.text,
    margin: 0,
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 9.2,
    y: 1.25,
    w: 2.6,
    h: 3.9,
    rectRadius: 0.08,
    line: { color: "D9E4F6", width: 1 },
    fill: { color: "F7FAFF" },
  });
  slide.addText("中期检查", {
    x: 9.55,
    y: 2.15,
    w: 1.9,
    h: 0.34,
    fontFace: "Microsoft YaHei",
    fontSize: 20,
    bold: true,
    align: "center",
    color: C.navy,
    margin: 0,
  });
  slide.addText("PPT", {
    x: 9.55,
    y: 2.62,
    w: 1.9,
    h: 0.42,
    fontFace: "Microsoft YaHei",
    fontSize: 28,
    bold: true,
    align: "center",
    color: C.blue,
    margin: 0,
  });
  finalizeSlide(slide, 1);
}

function addNewAgenda() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "汇报目录", "本次汇报重点介绍中期阶段已经完成的系统功能、当前问题与后续计划。");
  const items = [
    "项目定位与当前阶段成果",
    "系统设计：需求、架构、流程",
    "已实现功能与系统界面展示",
    "接口设计与数据库设计",
    "当前核心问题与下一步计划",
  ];
  items.forEach((item, index) => {
    const y = 1.6 + index * 0.86;
    addSimpleRow(slide, 1.0, y, 10.95, 0.56, `0${index + 1}`, item, index % 2 === 0 ? "F7FAFF" : "FFFFFF");
  });
  finalizeSlide(slide, 2);
}

function addPositionSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "项目定位与当前阶段成果", "本项目面向 SOP 执行规范性评测场景，当前已经完成系统主体功能落地。");
  addPanel(slide, 0.95, 1.5, 5.35, 4.8, "项目定位");
  addBulletList(slide, [
    "面向标准操作流程的制定、执行、评测与复核场景",
    "以“完整视频上传 + 多模态智能评测”为主要实现路径",
    "目标是形成一个可演示、可管理、可留痕的闭环系统",
  ], 1.18, 1.98, 4.88, { rowH: 0.66, fontSize: 12.4, bulletColor: C.blue });
  addPanel(slide, 6.7, 1.5, 5.45, 4.8, "当前阶段已经完成的工作");
  addBulletList(slide, [
    "完成前后端分离架构搭建，管理端与用户端已可运行",
    "完成用户登录、角色权限、SOP 管理与视频上传",
    "完成示范视频预处理、多阶段视频评测与结果后处理",
    "完成异步任务、历史记录、人工复核和统计分析功能",
  ], 6.95, 1.98, 4.95, { rowH: 0.66, fontSize: 12.1, bulletColor: C.green });
  finalizeSlide(slide, 3);
}

function addRequirementSummarySlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "系统需求概览", "系统主要围绕管理员和普通用户两类角色展开设计。");
  addPanel(slide, 0.95, 1.5, 5.45, 4.9, "管理员侧需求");
  addBulletList(slide, [
    "创建 SOP，配置步骤说明、步骤类型、权重和前置依赖",
    "上传完整示范视频，生成步骤参考信息",
    "查看执行记录并进行人工复核",
    "查看统计分析结果并维护系统配置",
  ], 1.18, 1.98, 4.95, { rowH: 0.68, fontSize: 12.1, bulletColor: C.blue });
  addPanel(slide, 6.7, 1.5, 5.45, 4.9, "普通用户侧需求");
  addBulletList(slide, [
    "查看待执行 SOP 和步骤说明",
    "上传完整执行视频并提交评测任务",
    "查看任务进度、评测结果和问题说明",
    "查看历史记录与人工复核结论",
  ], 6.93, 1.98, 4.95, { rowH: 0.68, fontSize: 12.1, bulletColor: C.green });
  finalizeSlide(slide, 5);
}

function addOpeningModuleStatusSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "开题功能模块图对照", "在开题阶段规划的功能模块基础上，标注当前中期阶段的完成情况。");

  slide.addShape(pptx.ShapeType.roundRect, {
    x: 3.15,
    y: 1.38,
    w: 6.65,
    h: 0.62,
    rectRadius: 0.06,
    line: { color: "C7D7EF", width: 1 },
    fill: { color: "F8FBFF" },
  });
  slide.addText("SOP 管理与智能评测系统", {
    x: 3.15,
    y: 1.58,
    w: 6.65,
    h: 0.18,
    fontFace: "Microsoft YaHei",
    fontSize: 15,
    bold: true,
    color: C.text,
    align: "center",
    margin: 0,
  });

  slide.addShape(pptx.ShapeType.line, {
    x: 6.48,
    y: 2.0,
    w: 0,
    h: 0.24,
    line: { color: "C7D7EF", width: 1.2 },
  });
  slide.addShape(pptx.ShapeType.line, {
    x: 2.45,
    y: 2.24,
    w: 8.05,
    h: 0,
    line: { color: "C7D7EF", width: 1.2 },
  });

  addModuleStatusCard(slide, 0.85, 2.42, 3.55, 1.42, "用户与权限模块", [
    "登录注册与角色路由",
    "管理员 / 普通用户隔离",
    "用户启用禁用与会话校验",
  ], "已完成", C.green, "F7FFFB");
  addModuleStatusCard(slide, 4.85, 2.42, 3.55, 1.42, "SOP 建模与示范管理", [
    "SOP 创建与步骤配置",
    "示范视频上传与预处理",
    "步骤参考信息维护",
  ], "已完成", C.green, "F7FFFB");
  addModuleStatusCard(slide, 8.85, 2.42, 3.55, 1.42, "用户执行与任务提交", [
    "SOP 浏览与步骤查看",
    "执行视频上传",
    "异步评测任务创建",
  ], "已完成", C.green, "F7FFFB");
  addModuleStatusCard(slide, 0.85, 4.28, 3.55, 1.42, "智能评测模块", [
    "时序分割与分步评测",
    "全局顺序校验",
    "规则评分与问题标签",
  ], "已完成", C.green, "F7FFFB");
  addModuleStatusCard(slide, 4.85, 4.28, 3.55, 1.42, "结果闭环与数据管理", [
    "历史记录与人工复核",
    "统计分析与媒体存储",
    "接口与数据库联动",
  ], "已完成", C.green, "F7FFFB");
  addModuleStatusCard(slide, 8.85, 4.28, 3.55, 1.42, "效果优化与反馈增强", [
    "多场景样本扩展",
    "评测稳定性优化",
    "问题片段与建议细化",
  ], "未完成", C.amber, "FFFBF2");

  addStatusTag(slide, "已完成", 9.15, 6.22, 0.78, C.green);
  slide.addText("主体功能已完成并联调", {
    x: 10.05,
    y: 6.28,
    w: 1.6,
    h: 0.12,
    fontFace: "Microsoft YaHei",
    fontSize: 9.2,
    color: C.subtext,
    margin: 0,
  });
  addStatusTag(slide, "未完成", 0.95, 6.22, 0.78, C.amber);
  slide.addText("后续重点是评测效果与反馈体验优化", {
    x: 1.85,
    y: 6.28,
    w: 2.7,
    h: 0.12,
    fontFace: "Microsoft YaHei",
    fontSize: 9.2,
    color: C.subtext,
    margin: 0,
  });

  finalizeSlide(slide, 4);
}

function addArchitectureAppleSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "系统总体架构", "采用前后端分离 + 异步 Worker + 多模态模型调用的整体架构。");
  addPanel(slide, 0.95, 1.8, 2.3, 1.0, "前端层");
  addBodyText(slide, "Vue 3\n管理员端 / 用户端", 1.15, 2.12, 1.9, 0.42, {
    minFontSize: 11,
    maxFontSize: 11,
    color: C.subtext,
    align: "center",
  });
  addPanel(slide, 3.7, 1.8, 2.6, 1.0, "接口层");
  addBodyText(slide, "FastAPI\n鉴权 / 业务 API", 3.92, 2.12, 2.15, 0.42, {
    minFontSize: 11,
    maxFontSize: 11,
    color: C.subtext,
    align: "center",
  });
  addPanel(slide, 6.82, 1.8, 2.6, 1.0, "处理层");
  addBodyText(slide, "Evaluation Worker\n异步任务处理", 7.04, 2.12, 2.15, 0.42, {
    minFontSize: 11,
    maxFontSize: 11,
    color: C.subtext,
    align: "center",
  });
  addPanel(slide, 9.95, 1.8, 2.2, 1.0, "模型层");
  addBodyText(slide, "多模态大模型\n视频理解与判定", 10.15, 2.12, 1.8, 0.42, {
    minFontSize: 10.5,
    maxFontSize: 10.5,
    color: C.subtext,
    align: "center",
  });
  [[3.25, 2.3, 0.45], [6.4, 2.3, 0.42], [9.52, 2.3, 0.38]].forEach((line) => {
    slide.addShape(pptx.ShapeType.line, {
      x: line[0],
      y: line[1],
      w: line[2],
      h: 0,
      line: { color: C.blue, width: 1.4 },
    });
  });
  addPanel(slide, 1.35, 3.55, 4.75, 2.05, "数据与媒体");
  addBulletList(slide, [
    "MySQL 存储用户、SOP、任务与结果数据",
    "本地文件系统存储示范视频、执行视频和关键帧",
    "为历史查询、统计分析和复核提供支撑",
  ], 1.58, 4.0, 4.25, { rowH: 0.48, fontSize: 11.2, bulletColor: C.teal });
  addPanel(slide, 6.55, 3.55, 4.95, 2.05, "关键能力");
  addBulletList(slide, [
    "OpenCV / FFmpeg：视频处理与抽帧",
    "httpx：模型接口调用",
    "规则后处理：权重、依赖与问题扣分",
  ], 6.78, 4.0, 4.45, { rowH: 0.48, fontSize: 11.2, bulletColor: C.amber });
  finalizeSlide(slide, 6);
}

function addFlowAppleSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "核心业务流程", "形成“管理员建模—用户执行—系统评测—结果复核”的完整闭环。");
  addStepFlow(slide, [
    "管理员创建 SOP",
    "上传示范视频并生成参考信息",
    "用户上传执行视频",
    "系统异步评测并生成结果",
    "查看结果、统计分析与人工复核",
  ], 0.95, 1.95, 11.2, [C.blue, C.teal, C.green, C.amber, C.navy]);
  addPanel(slide, 0.95, 3.45, 11.2, 2.15, "流程特点");
  addBulletList(slide, [
    "用户一次性上传完整执行视频，减少逐步操作负担。",
    "系统通过多阶段评测链路完成时序分析、分步判断和全局校验。",
    "所有结果均沉淀到历史记录中，支持后续复核与统计分析。",
  ], 1.18, 3.95, 10.7, { rowH: 0.56, fontSize: 11.6, bulletColor: C.blue });
  finalizeSlide(slide, 7);
}

function addSopPreprocessDiagramSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "SOP 预处理流程图", "展示管理员上传完整示范视频后，系统如何生成步骤级参考信息。");
  addFlowNode(slide, 0.95, 2.1, 2.15, 1.55, "输入", "管理员创建 SOP，并上传完整流程示范视频。", C.blue);
  addArrow(slide, 3.15, 2.88, 0.55, C.blue);
  addFlowNode(slide, 3.75, 2.1, 2.15, 1.55, "分段", "系统依据步骤描述与流程顺序，识别各步骤的大致时间区间。", C.teal);
  addArrow(slide, 5.95, 2.88, 0.55, C.teal);
  addFlowNode(slide, 6.55, 2.1, 2.15, 1.55, "抽帧", "从候选区间内抽取关键帧与分析帧，形成视觉参考样本。", C.green);
  addArrow(slide, 8.75, 2.88, 0.55, C.green);
  addFlowNode(slide, 9.35, 2.1, 2.15, 1.55, "生成", "生成参考摘要、关键时刻与 ROI 提示，构成步骤参考包。", C.amber);

  addPanel(slide, 0.95, 4.35, 11.2, 1.75, "流程说明");
  addBulletList(slide, [
    "该流程的目标是把“整段示范视频”转换为“可用于步骤级比对的标准参考信息”。",
    "预处理结果将直接服务于后续执行视频的分步评测和顺序校验。",
    "当前系统已支持自动生成，后续还会继续优化步骤边界识别与人工微调能力。",
  ], 1.18, 4.78, 10.7, { rowH: 0.42, fontSize: 11.1, bulletColor: C.blue });
  finalizeSlide(slide, 8);
}

function addUserEvaluationDiagramSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "用户侧评估链路流程图", "展示普通用户提交执行视频后，系统如何完成异步评估与结果闭环。");
  addFlowNode(slide, 0.95, 1.95, 2.0, 1.45, "提交", "用户选择 SOP，上传完整执行视频并发起评测。", C.green);
  addArrow(slide, 3.0, 2.68, 0.5, C.green);
  addFlowNode(slide, 3.55, 1.95, 2.05, 1.45, "建任务", "后端创建 evaluation_job，并进入异步处理队列。", C.blue);
  addArrow(slide, 5.65, 2.68, 0.5, C.blue);
  addFlowNode(slide, 6.2, 1.95, 2.05, 1.45, "评测", "Worker 执行时序分析、分步评测和全局校验。", C.amber);
  addArrow(slide, 8.3, 2.68, 0.5, C.amber);
  addFlowNode(slide, 8.85, 1.95, 2.1, 1.45, "出结果", "生成总分、步骤得分、问题标签和证据说明。", C.teal);
  addArrow(slide, 10.98, 2.68, 0.38, C.teal);
  addFlowNode(slide, 0.95, 4.2, 2.0, 1.45, "留痕", "结果写入历史记录，支持后续查询和人工复核。", C.navy);
  addArrow(slide, 3.0, 4.93, 0.5, C.navy);
  addFlowNode(slide, 3.55, 4.2, 2.05, 1.45, "展示", "前端展示任务进度、日志、评估结果和历史信息。", C.green);

  addPanel(slide, 6.2, 4.2, 5.95, 1.45, "链路特点");
  addBulletList(slide, [
    "用户侧采用完整视频一次性上传，避免逐步骤提交的复杂操作。",
    "任务处理采用异步机制，适合视频评估这一耗时场景。",
    "最终形成“提交—评估—展示—留痕”的闭环链路。",
  ], 6.45, 4.52, 5.45, { rowH: 0.3, fontSize: 10.4, bulletColor: C.blue });
  finalizeSlide(slide, 13);
}

function addProgressSummarySlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "总体进展", "当前汇报重点不再强调阶段数字，而是展示已经完成的系统功能。");
  addPanel(slide, 0.95, 1.55, 11.2, 4.95, "已实现功能总览");
  const features = [
    "用户登录、注册、角色权限控制",
    "SOP 创建、步骤配置、示范视频上传与管理",
    "示范视频预处理与步骤参考信息生成",
    "用户执行视频上传与异步任务处理",
    "多阶段视频评测与规则后处理",
    "历史记录查询、人工复核与统计分析",
    "评测过程展开显示与结果可解释展示",
  ];
  features.forEach((item, index) => {
    const col = index < 4 ? 0 : 1;
    const row = col === 0 ? index : index - 4;
    addSimpleRow(
      slide,
      1.18 + col * 5.35,
      2.05 + row * 0.88,
      4.95,
      0.56,
      `功能 ${index + 1}`,
      item,
      row % 2 === 0 ? "F8FBFF" : "FFFFFF"
    );
  });
  finalizeSlide(slide, 9);
}

function addAdminFeatureSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "已实现功能：管理员端", "管理员端主要负责 SOP 建模、示范视频维护与结果管理。");
  addPanel(slide, 0.95, 1.55, 5.45, 4.75, "已落地能力");
  addBulletList(slide, [
    "SOP 列表管理、新建、删除和详情查看",
    "步骤类型、步骤权重、前置依赖与扣分参数配置",
    "完整示范视频上传与步骤级参考信息生成",
    "步骤参考信息手动覆盖和内容修正",
  ], 1.18, 2.02, 4.95, { rowH: 0.66, fontSize: 12, bulletColor: C.blue });
  addPanel(slide, 6.7, 1.55, 5.45, 4.75, "阶段评价");
  addBodyText(slide, "管理员端已经能支撑从 SOP 建模到示范数据维护的主要工作流程，说明系统在“标准参考构建”这一关键环节上已具备可运行能力。", 6.98, 2.05, 4.9, 0.88, {
    minFontSize: 12,
    maxFontSize: 12,
    color: C.text,
    leading: 1.3,
  });
  addShotPlaceholder(slide, 7.0, 3.2, 4.85, 2.45, "管理端界面预留", "建议放 SOP 列表页 / 新建 SOP 弹窗截图");
  finalizeSlide(slide, 10);
}

function addUserEvalFeatureSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "已实现功能：用户端与评测端", "用户端负责执行与提交，评测端负责任务处理与结果生成。");
  addPanel(slide, 0.95, 1.55, 5.45, 4.75, "已落地能力");
  addBulletList(slide, [
    "查看待执行 SOP 任务及步骤说明",
    "上传完整执行视频并创建评测任务",
    "轮询任务进度、日志和失败原因",
    "获取步骤级得分、问题标签与证据说明",
  ], 1.18, 2.02, 4.95, { rowH: 0.66, fontSize: 12, bulletColor: C.green });
  addPanel(slide, 6.7, 1.55, 5.45, 4.75, "评测端特点");
  addBulletList(slide, [
    "采用时序分割—分步评测—全局校验的多阶段设计",
    "结合规则后处理得到最终总分和通过结论",
    "支持长视频异步处理，适合实际操作场景",
  ], 6.95, 2.05, 4.95, { rowH: 0.62, fontSize: 11.6, bulletColor: C.amber });
  addShotPlaceholder(slide, 6.95, 3.75, 4.9, 1.7, "用户端 / 评测页预留", "建议放任务页、执行页或进度日志截图");
  finalizeSlide(slide, 11);
}

function addResultClosureSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "已实现功能：结果闭环与分析", "系统已经具备“结果记录—人工复核—统计分析”的后续管理能力。");
  addPanel(slide, 0.95, 1.55, 3.55, 4.7, "历史记录");
  addBulletList(slide, [
    "保存每次评测的总分、问题标签与步骤结果",
    "支持查看执行视频和过程摘要",
    "支撑个人历史查询与回看",
  ], 1.18, 2.05, 3.08, { rowH: 0.68, fontSize: 11.3, bulletColor: C.blue });
  addPanel(slide, 4.78, 1.55, 3.55, 4.7, "人工复核");
  addBulletList(slide, [
    "管理员可对结果执行通过 / 不通过 / 需整改处理",
    "保留人工意见，避免完全依赖单次模型判断",
    "形成 AI 与人工结合的判定闭环",
  ], 5.02, 2.05, 3.08, { rowH: 0.68, fontSize: 11.3, bulletColor: C.green });
  addPanel(slide, 8.6, 1.55, 3.55, 4.7, "统计分析");
  addBulletList(slide, [
    "支持 SOP 维度统计和问题类型统计",
    "能够从结果中识别高频异常步骤",
    "为后续优化 SOP 或培训提供依据",
  ], 8.84, 2.05, 3.08, { rowH: 0.68, fontSize: 11.3, bulletColor: C.amber });
  finalizeSlide(slide, 12);
}

function addInterfaceDesignSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "接口设计概览", "接口按认证、SOP、评测、历史与统计等模块划分，支撑系统主要业务流程。");
  addPanel(slide, 0.95, 1.5, 5.45, 4.9, "主要接口及作用");
  const apiRows = [
    ["/api/auth/*", "完成登录、注册、当前用户查询与退出"],
    ["/api/users / /api/config", "管理员维护用户状态与模型参数配置"],
    ["/api/sops", "SOP 列表、详情、新建、删除与步骤参考维护"],
    ["/api/sops/{id}/evaluation-jobs", "创建评测任务并提交用户视频"],
    ["/api/evaluation-jobs/*", "查询任务状态、进度日志与失败原因"],
    ["/api/history / /api/stats", "历史记录查询、人工复核与统计分析"],
    ["/api/media/{id}", "按权限访问示范视频、执行视频与关键帧资源"],
  ];
  apiRows.forEach((row, index) => {
    addSimpleRow(slide, 1.15, 2.0 + index * 0.55, 5.0, 0.42, row[0], row[1], index % 2 === 0 ? "F8FBFF" : "FFFFFF");
  });
  addPanel(slide, 6.7, 1.5, 5.45, 4.9, "接口设计特点");
  addBulletList(slide, [
    "接口结构与前端页面职责保持一致，便于联调和后续维护。",
    "评测任务和历史记录分离，既满足异步处理也方便结果留痕。",
    "媒体资源通过统一接口按权限访问，便于示范视频和执行视频复用。",
    "SOP 相关接口不仅服务于基础增删改查，还承载参考信息维护能力。",
  ], 6.95, 2.0, 4.95, { rowH: 0.66, fontSize: 11.4, bulletColor: C.teal });
  finalizeSlide(slide, 14);
}

function addDatabaseDesignV2() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "数据库设计", "数据库围绕用户、SOP、媒体、任务、执行结果和复核记录建立关联。");
  const rowsLeft = [
    ["users", "保存用户账号、角色和状态信息"],
    ["user_login_sessions", "保存登录会话与当前在线状态"],
    ["ai_configs", "保存模型接口相关配置"],
    ["sops", "保存 SOP 主体信息"],
    ["sop_steps", "保存步骤描述、类型、权重等信息"],
    ["sop_step_prerequisites", "保存步骤前置依赖关系"],
  ];
  const rowsRight = [
    ["media_files", "保存示范视频、执行视频和媒体索引"],
    ["sop_step_keyframes", "保存步骤关键帧数据"],
    ["sop_step_substeps", "保存关键时刻与时间点信息"],
    ["evaluation_jobs", "保存异步评测任务及状态"],
    ["sop_executions", "保存每次执行与总体评测结果"],
    ["execution_step_results", "保存步骤级得分与证据"],
    ["manual_reviews", "保存人工复核结论与备注"],
  ];
  addPanel(slide, 0.95, 1.55, 5.45, 4.9, "核心数据表及作用（一）");
  rowsLeft.forEach((row, index) => {
    addSimpleRow(slide, 1.15, 1.98 + index * 0.62, 5.05, 0.48, row[0], row[1], index % 2 === 0 ? "F8FBFF" : "FFFFFF");
  });
  addPanel(slide, 6.7, 1.55, 5.45, 4.9, "核心数据表及作用（二）");
  rowsRight.forEach((row, index) => {
    addSimpleRow(slide, 6.9, 1.98 + index * 0.54, 5.05, 0.42, row[0], row[1], index % 2 === 0 ? "F8FBFF" : "FFFFFF");
  });
  finalizeSlide(slide, 15);
}

function addScreenshotAdminSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "系统界面展示：管理端", "预留大面积空间用于放置系统截图。");
  addShotPlaceholder(slide, 0.95, 1.55, 7.45, 4.95, "管理端主界面截图", "建议放 SOP 列表 / 数据统计 / 复核界面");
  addShotPlaceholder(slide, 8.72, 1.55, 3.4, 2.35, "局部截图 1", "建议放新建 SOP 弹窗");
  addShotPlaceholder(slide, 8.72, 4.15, 3.4, 2.35, "局部截图 2", "建议放步骤配置或参考信息维护");
  finalizeSlide(slide, 16);
}

function addScreenshotUserSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "系统界面展示：用户端", "预留执行流程和任务页的展示空间。");
  addShotPlaceholder(slide, 0.95, 1.55, 5.45, 4.95, "用户端任务页截图", "建议放任务列表 / 上传视频页面");
  addShotPlaceholder(slide, 6.7, 1.55, 5.45, 4.95, "任务进度截图", "建议放异步任务状态、日志或轮询结果");
  finalizeSlide(slide, 17);
}

function addScreenshotResultSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "系统界面展示：评测结果", "预留结果页、历史记录和过程展开的展示空间。");
  addShotPlaceholder(slide, 0.95, 1.55, 7.25, 4.95, "结果页截图", "建议放总分、步骤得分、问题标签和时间轴");
  addShotPlaceholder(slide, 8.48, 1.55, 3.65, 2.35, "历史记录截图", "建议放历史页或复核结论");
  addShotPlaceholder(slide, 8.48, 4.15, 3.65, 2.35, "过程展开截图", "建议放评测过程或 Token 信息");
  finalizeSlide(slide, 18);
}

function addProblemsCoreSlide() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "当前存在的核心问题", "问题聚焦于项目本身的评测效果、建模精度和场景适应能力。");
  const items = [
    ["评测结果稳定性仍不足", "不同拍摄角度、光照、遮挡和清晰度条件下，同一动作的判断结果仍可能波动。", C.red],
    ["复杂时序动作识别难度较高", "对于顺序依赖强、步骤衔接紧密的 SOP，步骤定位和顺序判断仍可能偏差。", C.amber],
    ["示范视频到步骤映射仍不够精细", "完整流程视频自动切分虽已实现，但部分步骤边界不明显，影响参考质量。", C.blue],
    ["系统场景泛化能力仍有待提升", "当操作对象、拍摄环境或流程类型变化较大时，模型适应性仍需增强。", C.green],
    ["评测解释性仍可继续增强", "目前已能输出得分和证据，但“错在哪里、如何改进”还可以表达得更直观。", C.teal],
  ];
  items.forEach((item, index) => {
    const col = index < 3 ? 0 : 1;
    const row = col === 0 ? index : index - 3;
    const x = col === 0 ? 0.95 : 6.55;
    const y = 1.7 + row * 1.45;
    addPanel(slide, x, y, 5.6, 1.15, "", { fillColor: index % 2 === 0 ? "F8FBFF" : "FFFFFF" });
    addPill(slide, `问题 ${index + 1}`, x + 0.16, y + 0.14, 0.82, item[2]);
    slide.addText(item[0], {
      x: x + 1.1,
      y: y + 0.16,
      w: 4.2,
      h: 0.2,
      fontFace: "Microsoft YaHei",
      fontSize: 12,
      bold: true,
      color: C.text,
      margin: 0,
    });
    addBodyText(slide, item[1], x + 0.16, y + 0.48, 5.12, 0.44, {
      minFontSize: 10.2,
      maxFontSize: 10.2,
      color: C.subtext,
      leading: 1.18,
    });
  });
  finalizeSlide(slide, 19);
}

function addPlanV2() {
  const slide = pptx.addSlide();
  addBg(slide);
  addTitle(slide, "改进措施与下一步计划", "下一阶段重点从“功能搭建”转向“效果优化”和“展示完善”。");
  addStepFlow(slide, [
    "优化评测提示词与判定规则",
    "增强时序分析能力",
    "改进参考信息生成方式",
    "扩展多场景样本与 SOP 类型",
    "强化结果展示与反馈能力",
  ], 0.95, 1.95, 11.2, [C.blue, C.green, C.amber, C.teal, C.navy]);
  addPanel(slide, 0.95, 3.45, 11.2, 2.1, "具体计划");
  addBulletList(slide, [
    "补充关键动作、顺序约束和异常情况的判定规则，提高模型判断一致性。",
    "继续优化短时动作、相邻步骤和前置依赖步骤的识别与定位效果。",
    "优化关键帧、关键时刻和 ROI 提取策略，必要时保留人工微调入口。",
    "增加不同场景和不同流程类型样本，提升系统泛化能力和适用范围。",
    "让结果页与时间轴、问题片段和改进建议之间形成更清晰的对应关系。",
  ], 1.18, 3.88, 10.72, { rowH: 0.34, fontSize: 10.9, bulletColor: C.blue });
  finalizeSlide(slide, 20);
}

function addThanksSlide() {
  const slide = pptx.addSlide();
  addBg(slide, true);
  slide.addText("致谢", {
    x: 0.92,
    y: 1.45,
    w: 2.0,
    h: 0.36,
    fontFace: "Microsoft YaHei",
    fontSize: 28,
    bold: true,
    color: C.white,
    margin: 0,
  });
  slide.addText("感谢老师的指导与评阅", {
    x: 0.95,
    y: 2.35,
    w: 5.2,
    h: 0.36,
    fontFace: "Microsoft YaHei",
    fontSize: 20,
    color: "D7E6FF",
    margin: 0,
  });
  slide.addText("恳请各位老师批评指正", {
    x: 0.95,
    y: 2.9,
    w: 4.8,
    h: 0.28,
    fontFace: "Microsoft YaHei",
    fontSize: 16,
    color: "D7E6FF",
    margin: 0,
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 8.95,
    y: 1.45,
    w: 2.7,
    h: 3.1,
    rectRadius: 0.08,
    line: { color: "31538E", width: 1 },
    fill: { color: "15305F" },
  });
  slide.addText("Thank\nYou", {
    x: 9.35,
    y: 2.0,
    w: 1.9,
    h: 1.0,
    fontFace: "Microsoft YaHei",
    fontSize: 24,
    bold: true,
    align: "center",
    color: C.white,
    margin: 0,
    valign: "mid",
  });
  finalizeSlide(slide, 21, true);
}

async function main() {
  addMinimalCover();
  addNewAgenda();
  addPositionSlide();
  addOpeningModuleStatusSlide();
  addRequirementSummarySlide();
  addArchitectureAppleSlide();
  addFlowAppleSlide();
  addSopPreprocessDiagramSlide();
  addProgressSummarySlide();
  addAdminFeatureSlide();
  addUserEvalFeatureSlide();
  addResultClosureSlide();
  addUserEvaluationDiagramSlide();
  addInterfaceDesignSlide();
  addDatabaseDesignV2();
  addScreenshotAdminSlide();
  addScreenshotUserSlide();
  addScreenshotResultSlide();
  addProblemsCoreSlide();
  addPlanV2();
  addThanksSlide();
  await pptx.writeFile({ fileName: outputFile });
  console.log(`PPT generated: ${outputFile}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
