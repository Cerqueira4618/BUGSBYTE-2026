<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

type LoginUser = {
  email: string
  password: string
}

const DEFAULT_USERS: LoginUser[] = [
  {
    email: 'admin@cryptobyte.com',
    password: '123456',
  },
]

const router = useRouter()
const email = ref('')
const password = ref('')
const errorMessage = ref('')

const getExistingUsers = (): LoginUser[] => {
  const rawUsers = localStorage.getItem('users')

  if (!rawUsers) {
    return DEFAULT_USERS
  }

  try {
    const parsed = JSON.parse(rawUsers)
    if (!Array.isArray(parsed)) {
      return DEFAULT_USERS
    }

    return parsed.filter(
      (user): user is LoginUser =>
        typeof user?.email === 'string' && typeof user?.password === 'string',
    )
  } catch {
    return DEFAULT_USERS
  }
}

const handleLogin = () => {
  errorMessage.value = ''

  const normalizedEmail = email.value.trim().toLowerCase()
  const typedPassword = password.value

  const users = getExistingUsers()
  const validUser = users.find(
    (user) =>
      user.email.trim().toLowerCase() === normalizedEmail &&
      user.password === typedPassword,
  )

  if (!validUser) {
    localStorage.setItem('isAuthenticated', 'false')
    errorMessage.value = 'Email ou senha inválidos. Verifique os dados e tente novamente.'
    return
  }

  localStorage.setItem('isAuthenticated', 'true')
  localStorage.setItem('currentUserEmail', validUser.email)
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
        <input id="email" v-model="email" type="email" placeholder="seuemail@dominio.com" required />

        <label for="password">Senha</label>
        <input id="password" v-model="password" type="password" placeholder="••••••••" required />
        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        <p class="help-message">Conta de teste: admin@cryptobyte.com / 123456</p>
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

.error-message {
  margin: 0;
  font-size: 13px;
  color: #ff9ea1;
}

.help-message {
  margin: 0;
  font-size: 12px;
  color: rgba(232, 240, 252, 0.68);
}
</style>
