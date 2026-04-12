# User Token Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在用户端历史记录列表和当前评测结果卡片显示 token 使用信息。

**Architecture:** 抽取用户端历史记录归一化与评测结果映射的纯函数模块，先用 Node 内置测试覆盖 `tokenUsage` 映射，再在 `User.vue` 复用这些函数并补两个展示点。后端接口与存储结构保持不变。

**Tech Stack:** Vue 3、Node `node:test`

---

### Task 1: 抽取并验证历史记录映射

**Files:**
- Create: `D:\毕业设计\bysj\src\utils\user-history.mjs`
- Create: `D:\毕业设计\bysj\tests\user-history.test.mjs`

- [ ] **Step 1: 写失败测试**
- [ ] **Step 2: 运行测试确认失败**
- [ ] **Step 3: 写最小实现**
- [ ] **Step 4: 运行测试确认通过**

### Task 2: 接入用户端展示

**Files:**
- Modify: `D:\毕业设计\bysj\src\views\User.vue`

- [ ] **Step 1: 复用纯函数模块替换内联映射**
- [ ] **Step 2: 在历史记录列表展示 token**
- [ ] **Step 3: 在当前评测结果卡片展示 token**
- [ ] **Step 4: 运行前端测试与构建验证**
