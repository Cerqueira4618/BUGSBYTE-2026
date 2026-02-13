<script setup lang="ts">
</script>

<template>
  <div class="app-container">
    <header class="app-header">
      <h1>Meu Projeto</h1>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
    <footer class="app-footer">
      <p>&copy; 2026 Meu Projeto</p>
    </footer>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f5f5f5;
}

.app-header {
  background-color: #333;
  color: white;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.app-header h1 {
  margin: 0;
  font-size: 28px;
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
