import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import DataUploadView from '../views/DataUploadView.vue'
import PreprocessingView from '../views/PreprocessingView.vue'
import PreviewExportView from '../views/PreviewExportView.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/upload',
    name: 'upload',
    component: DataUploadView
  },
  {
    path: '/preprocessing',
    name: 'preprocessing',
    component: PreprocessingView
  },
  {
    path: '/preview',
    name: 'preview',
    component: PreviewExportView
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router