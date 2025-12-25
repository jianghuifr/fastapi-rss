import { createRouter, createWebHistory } from 'vue-router'
import Reader from '../views/Reader.vue'

const routes = [
  {
    path: '/',
    redirect: '/reader'
  },
  {
    path: '/reader',
    name: 'Reader',
    component: Reader,
    props: (route) => ({ feedId: route.query.feed_id ? parseInt(route.query.feed_id) : null })
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
