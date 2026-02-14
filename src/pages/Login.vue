<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const handleLogin = () => {
  localStorage.setItem('isAuthenticated', 'true')
  router.push({ name: 'Simulator' })
}
</script>

<template>
  <section class="login-page">
    <div class="login-card">
      <h1>Login</h1>
      <p class="subtitle">Entre para acessar sua área e usar o simulador.</p>

      <form class="login-form" @submit.prevent="handleLogin">
        <label for="email">E-mail</label>
        <input id="email" type="email" placeholder="seuemail@dominio.com" required />

        <label for="password">Senha</label>
        <input id="password" type="password" placeholder="••••••••" required />
        <button type="submit">Entrar</button>
      </form>
    </div>
  </section>
</template>

<style scoped>
.login-page {
  min-height: calc(100vh - 190px);
  display: grid;
  place-items: center;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 420px;
  padding: 28px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(14, 28, 45, 0.92) 0%, rgba(9, 20, 34, 0.92) 100%);
  border: 1px solid rgba(95, 126, 166, 0.2);
  box-shadow: 0 18px 30px rgba(0, 0, 0, 0.35);
}

h1 {
  margin: 0;
  font-size: 28px;
}

.subtitle {
  margin: 8px 0 20px;
  color: rgba(232, 240, 252, 0.8);
}

.login-form {
  display: grid;
  gap: 10px;
}

label {
  font-weight: 600;
  font-size: 14px;
}

input {
  background: rgba(5, 15, 27, 0.9);
  color: #fff;
  border: 1px solid rgba(95, 126, 166, 0.35);
  border-radius: 10px;
  padding: 12px;
  outline: none;
}

input:focus {
  border-color: rgba(102, 239, 139, 0.8);
}

button {
  margin-top: 8px;
  border: none;
  border-radius: 999px;
  padding: 12px;
  background: #66ef8b;
  color: #031018;
  font-weight: 700;
  cursor: pointer;
}
</style>
