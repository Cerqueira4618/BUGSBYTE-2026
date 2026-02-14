<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useWebSocketStore } from './stores/websocket'

const router = useRouter()
const route = useRoute()
const websocketStore = useWebSocketStore()

const isAuthenticated = ref(localStorage.getItem('isAuthenticated') === 'true')
const currentUserEmail = ref(localStorage.getItem('currentUserEmail') || '')
const showScrollTop = ref(false)

const onScroll = () => {
  showScrollTop.value = window.scrollY > 300
}

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// Iniciar WebSocket quando o App é montado
onMounted(() => {
  websocketStore.startArbitrageSocket()
  window.addEventListener('scroll', onScroll)
})

// Desconectar quando o App é desmontado
onBeforeUnmount(() => {
  websocketStore.disconnectSocket()
  window.removeEventListener('scroll', onScroll)
})

// Atualiza o estado quando a rota muda
watch(
  () => route.path,
  () => {
    isAuthenticated.value = localStorage.getItem('isAuthenticated') === 'true'
    currentUserEmail.value = localStorage.getItem('currentUserEmail') || ''
  },
)

const handleLogout = () => {
  localStorage.setItem('isAuthenticated', 'false')
  localStorage.removeItem('currentUserEmail')
  isAuthenticated.value = false
  currentUserEmail.value = ''
  router.push({ name: 'Login' })
}

const userDisplay = computed(() => {
  if (!currentUserEmail.value) return ''
  const emailPart = currentUserEmail.value.split('@')[0]
  if (!emailPart) return ''
  return emailPart.charAt(0).toUpperCase() + emailPart.slice(1)
})
</script>

<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-shell">
        <div class="header-inner">
          <RouterLink :to="{ name: 'Home' }" class="brand">
            <img
              class="brand-mark"
              src="/bitcoin-cash-coin-crypto-3d-illustration-png.png"
              alt="Bitcoin"
            />
            <span class="brand-text">CryptoByte</span>
          </RouterLink>
          <nav class="main-nav">
            <RouterLink
              :to="{ name: 'Simulator' }"
              class="nav-item"
              active-class="nav-item-active"
              >Simulador</RouterLink
            >
            <RouterLink
              :to="{ name: 'Market' }"
              class="nav-item"
              active-class="nav-item-active"
              >Mercado</RouterLink
            >
            <RouterLink
              :to="{ name: 'Help' }"
              class="nav-item"
              active-class="nav-item-active"
              >Ajuda</RouterLink
            >
          </nav>
          <div class="actions">
            <span class="status-pill" :class="websocketStore.socketState">
              {{ websocketStore.socketState }}
            </span>
            <span v-if="isAuthenticated" class="user-greeting">
              👤 {{ userDisplay }}
            </span>
            <RouterLink v-if="!isAuthenticated" :to="{ name: 'Login' }" class="cta">
              <span>Login</span>
              <span class="arrow">→</span>
            </RouterLink>
            <button v-else class="cta" @click="handleLogout">
              <span>Logout</span>
              <span class="arrow">←</span>
            </button>
          </div>
        </div>
      </div>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
    <footer class="app-footer">
      <p>&copy;CryptoByte</p>
    </footer>

    <button
      v-show="showScrollTop"
      class="scroll-top-btn"
      aria-label="Voltar ao topo"
      @click="scrollToTop"
    >⬆</button>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background:
    radial-gradient(
      circle at 8% 22%,
      rgba(70, 218, 124, 0.24) 0%,
      rgba(70, 218, 124, 0.08) 20%,
      transparent 38%
    ),
    radial-gradient(
      circle at 50% 48%,
      rgba(27, 92, 255, 0.18) 0%,
      rgba(9, 33, 78, 0.12) 25%,
      transparent 52%
    ),
    linear-gradient(180deg, #050f24 0%, #030a1a 40%, #010611 100%);
  color: #ffffff;
}

.app-header {
  padding: 16px 22px;
  position: sticky;
  top: 0;
  z-index: 40;
}

.header-shell {
  max-width: 1240px;
  margin: 0 auto;
  border-radius: 18px;
  background: linear-gradient(
    90deg,
    rgba(14, 28, 45, 0.96) 0%,
    rgba(12, 25, 41, 0.96) 100%
  );
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.32);
  border: 1px solid rgba(95, 126, 166, 0.08);
}

.header-inner {
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 14px 20px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
}

.brand-mark {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid rgba(102, 239, 139, 0.55);
  box-shadow: 0 0 10px rgba(102, 239, 139, 0.22);
}

.brand-text {
  color: #f4f8ff;
  font-size: 22px;
  line-height: 1;
  font-weight: 700;
}

.main-nav {
  display: flex;
  gap: 16px;
  margin-left: 10px;
  align-items: center;
}

.nav-item {
  color: rgba(232, 240, 252, 0.88);
  text-decoration: none;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 6px;
}

.nav-item-active {
  color: #63ea88;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.03);
  color: #dfffdc;
}

.actions {
  margin-left: auto;
  display: flex;
  gap: 14px;
  align-items: center;
}

.login-link {
  color: rgba(232, 240, 252, 0.92);
  text-decoration: none;
  padding: 6px 2px;
}

.cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #66ef8b;
  color: #031018;
  border: none;
  padding: 9px 16px;
  border-radius: 999px;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
  font-size: 14px;
}

.cta:hover {
  background: #4fd975;
  transform: scale(1.02);
  transition: all 0.2s ease;
}

.user-greeting {
  color: rgba(232, 240, 252, 0.95);
  font-weight: 600;
  font-size: 14px;
  padding: 6px 12px;
  background: rgba(102, 239, 139, 0.1);
  border-radius: 999px;
  border: 1px solid rgba(102, 239, 139, 0.3);
}

.arrow {
  font-size: 16px;
  line-height: 1;
}

.app-main {
  flex: 1;
  padding: 20px;
}

.app-footer {
  background-color: #333;
  color: white;
  text-align: center;
  padding: 15px;
  margin-top: auto;
}

.app-footer p {
  margin: 0;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 90px;
  padding: 6px 14px;
  border-radius: 999px;
  font-weight: 600;
  font-size: 12px;
  letter-spacing: 0.3px;
  text-transform: capitalize;
}

.status-pill.connected {
  background: linear-gradient(135deg, #103428, #0b2620);
  color: #bfffe0;
  border: 1.2px solid rgba(102, 239, 139, 0.6);
  box-shadow: 0 4px 8px rgba(102, 239, 139, 0.2);
}

.status-pill.disconnected {
  background: linear-gradient(135deg, #3a1f28, #2c161d);
  color: #ffd8d8;
  border: 1.2px solid rgba(255, 120, 120, 0.65);
  box-shadow: 0 4px 8px rgba(255, 120, 120, 0.18);
}

.scroll-top-btn {
  position: fixed;
  bottom: 28px;
  right: 28px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(102, 239, 139, 0.18);
  color: #66ef8b;
  border: 1px solid rgba(102, 239, 139, 0.4);
  font-size: 20px;
  line-height: 1;
  padding-bottom: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
  transition: background 0.2s, transform 0.2s;
  z-index: 50;
}

.scroll-top-btn:hover {
  background: rgba(102, 239, 139, 0.32);
  transform: scale(1.1);
}
</style>

<style>
html,
body,
#app {
  margin: 0;
  padding: 0;
  width: 100%;
  min-height: 100%;
  background: #000;
}
</style>
