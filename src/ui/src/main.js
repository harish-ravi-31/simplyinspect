import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'
import { useAuth } from './composables/useAuth'
import '@mdi/font/css/materialdesignicons.css'

const app = createApp(App)

// Initialize authentication
const auth = useAuth()
auth.setupAxiosInterceptors()
auth.initializeAuth()

app.use(router)
app.use(vuetify)

app.mount('#app')