<script setup lang="ts">
import { ref } from 'vue'

const users = ref([
  { id: 1, nome: 'João Silva', email: 'joao@example.com', idade: 28 },
  { id: 2, nome: 'Maria Santos', email: 'maria@example.com', idade: 34 },
  { id: 3, nome: 'Pedro Costa', email: 'pedro@example.com', idade: 25 },
  { id: 4, nome: 'Ana Oliveira', email: 'ana@example.com', idade: 31 }
])
</script>

<template>
  <div class="table-container">
    <h2>Lista de Utilizadores</h2>
    <table class="table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Nome</th>
          <th>Email</th>
          <th>Idade</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td>{{ user.id }}</td>
          <td>{{ user.nome }}</td>
          <td>{{ user.email }}</td>
          <td>{{ user.idade }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-container {
  padding: 20px;
}

.table {
  border-collapse: collapse;
  width: 100%;
  margin-top: 15px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.table thead {
  background-color: #f5f5f5;
  border-bottom: 2px solid #ddd;
}

.table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #333;
}

.table td {
  padding: 12px;
  border-bottom: 1px solid #ddd;
}

.table tbody tr:hover {
  background-color: #f9f9f9;
}
</style>
