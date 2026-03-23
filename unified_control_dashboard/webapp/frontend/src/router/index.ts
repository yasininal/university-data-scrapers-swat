import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import DataView from '../views/DataView.vue'
import GrantsView from '../views/GrantsView.vue'
import ItuView from '../views/ItuView.vue'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            name: 'home',
            component: HomeView,
        },
        {
            path: '/data',
            name: 'data',
            component: DataView,
        },
        {
            path: '/grants',
            name: 'grants',
            component: GrantsView,
        },
        {
            path: '/itu',
            name: 'itu',
            component: ItuView,
        },
    ],
})

export default router
