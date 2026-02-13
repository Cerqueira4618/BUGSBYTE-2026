import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Login',
    component: () => import('../components/LoginPage.vue'),
  },
  {
    path: '/main',
    name: 'Main',
    component: () => import('../pages/Main.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
