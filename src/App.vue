<script setup lang="ts">
</script>

<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-inner">
        <div class="left">
          <RouterLink :to="{ name: 'Main' }" class="logo-button">CryptoByte</RouterLink>
        </div>
        <nav class="main-nav">
          <a href="#" class="nav-item">Individuals</a>
          <a href="#" class="nav-item">Market</a>
          <a href="#" class="nav-item">Learn</a>
          <a href="#" class="nav-item">Transparency</a>
          <a href="#" class="nav-item">Enterprise</a>
        </nav>
        <div class="actions">
          <RouterLink :to="{ name: 'Login' }" class="login-link">Login</RouterLink>
          <button class="cta">Get started</button>
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
  background: rgba(6, 10, 15, 0.55);
  color: white;
  padding: 14px 24px;
  box-shadow: 0 8px 24px rgba(2,6,10,0.6);
  position: sticky;
  top: 0;
  z-index: 40;
}

.header-inner {
  display: flex;
  align-items: center;
  gap: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.main-nav {
  display: flex;
  gap: 18px;
  margin-left: 12px;
}

.nav-item {
  color: rgba(230,238,246,0.85);
  text-decoration: none;
  font-weight: 500;
  padding: 6px 8px;
  border-radius: 6px;
}

.nav-item:hover {
  background: rgba(255,255,255,0.02);
  color: #dfffdc;
}

.actions {
  margin-left: auto;
  display: flex;
  gap: 12px;
  align-items: center;
}

.login-link {
  color: rgba(230,238,246,0.85);
  text-decoration: none;
}

.cta {
  background: #46da7c;
  color: #031018;
  border: none;
  padding: 8px 14px;
  border-radius: 20px;
  font-weight: 700;
  cursor: pointer;
}

.app-header h1 {
  margin: 0;
  font-size: 28px;
}

.logo-button {
  color: white;
  text-decoration: none;
  padding: 6px 10px;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
}

.logo-button:hover {
  opacity: 0.9;
  text-decoration: underline;
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
