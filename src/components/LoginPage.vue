<script setup lang="ts">
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h2>Entrar</h2>
      <p class="subtitle">Faça login para continuar (demo estática)</p>
      <form class="login-form" @submit.prevent>
        <label>
          <span>Email</span>
          <input type="email" placeholder="seu@exemplo.com" />
        </label>
        <label>
          <span>Senha</span>
          <input type="password" placeholder="••••••••" />
        </label>
        <button type="submit" class="btn">Entrar</button>
      </form>
      <p class="small">Não funcional — apenas demonstração</p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 70vh;
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: #ffffff;
  padding: 28px;
  border-radius: 8px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.08);
  text-align: left;
}

.login-card h2 {
  margin: 0 0 8px 0;
  font-size: 22px;
}

.subtitle {
  margin: 0 0 16px 0;
  color: #666;
  font-size: 14px;
}

.login-form label {
  display: block;
  margin-bottom: 12px;
  font-size: 14px;
}

.login-form span {
  display: block;
  margin-bottom: 6px;
  color: #333;
}

.login-form input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.btn {
  display: inline-block;
  width: 100%;
  padding: 10px 12px;
  margin-top: 10px;
  background: #2d7cff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.small {
  margin-top: 12px;
  color: #888;
  font-size: 13px;
  text-align: center;
}
</style>
