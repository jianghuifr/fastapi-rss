import { createRouter, createWebHistory } from 'vue-router'
import Admin from '../views/Admin.vue'
import Reader from '../views/Reader.vue'

const routes = [
  {
    path: '/',
    redirect: '/reader'
  },
  {
    path: '/admin',
    name: 'Admin',
    component: Admin
  },
  {
    path: '/reader',
    name: 'Reader',
    component: Reader
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
