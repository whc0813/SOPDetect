import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { initializeAuthSessionSync } from './api/client'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/variables.css'
import './styles/base.css'
import './styles/components.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(router)
app.use(ElementPlus)

initializeAuthSessionSync(router)

app.mount('#app')
