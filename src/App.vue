<script setup lang="ts">
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
            <RouterLink :to="{ name: 'Simulator' }" class="nav-item" active-class="nav-item-active">Simulador</RouterLink>
            <RouterLink :to="{ name: 'Market' }" class="nav-item" active-class="nav-item-active">Mercado</RouterLink>
            <a href="#" class="nav-item">Learn</a>
            <a href="#" class="nav-item">Transparency</a>
            <a href="#" class="nav-item">Enterprise</a>
          </nav>
          <div class="actions">
            <RouterLink :to="{ name: 'Login' }" class="cta">
              <span>Login</span>
              <span class="arrow">→</span>
            </RouterLink>
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
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background:
    radial-gradient(circle at 8% 22%, rgba(70, 218, 124, 0.24) 0%, rgba(70, 218, 124, 0.08) 20%, transparent 38%),
    radial-gradient(circle at 50% 48%, rgba(27, 92, 255, 0.18) 0%, rgba(9, 33, 78, 0.12) 25%, transparent 52%),
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
  background: linear-gradient(90deg, rgba(14, 28, 45, 0.96) 0%, rgba(12, 25, 41, 0.96) 100%);
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
  gap: 24px;
  margin-left: 10px;
}

.nav-item {
  color: rgba(232, 240, 252, 0.88);
  text-decoration: none;
  font-weight: 500;
  padding: 6px 2px;
  border-radius: 6px;
}

.nav-item-active {
  color: #63ea88;
}

.nav-item:hover {
  background: rgba(255,255,255,0.03);
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
