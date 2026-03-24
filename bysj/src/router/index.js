import { createRouter, createWebHistory } from 'vue-router'
import { clearAuthSession, getCurrentUser } from '../api/client'
import Login from '../views/Login.vue'
import Admin from '../views/Admin.vue'
import User from '../views/User.vue'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { public: true }
  },
  {
    path: '/admin',
    name: 'Admin',
    component: Admin,
    meta: { requiresAuth: true, role: 'admin' }
  },
  {
    path: '/user',
    name: 'User',
    component: User,
    meta: { requiresAuth: true, role: 'user' }
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

router.beforeEach((to, from, next) => {
  const user = getCurrentUser()

  if (!to.meta?.requiresAuth) {
    if (to.path === '/login' && user) {
      next(user.role === 'admin' ? '/admin' : '/user')
      return
    }
    next()
    return
  }

  if (!user) {
    clearAuthSession()
    next('/login')
    return
  }

  if (to.meta?.role && user.role !== to.meta.role) {
    next(user.role === 'admin' ? '/admin' : '/user')
    return
  }

  next()
})

export default router
