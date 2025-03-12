<template>
  <div class="home">
    <el-card class="welcome-card">
      <template #header>
        <div class="card-header">
          <h2>Добро пожаловать в Конструктор предобработки данных</h2>
        </div>
      </template>
      <div class="card-content">
        <p>
          Это инструмент для анализа и предобработки наборов данных. Система анализирует данные, поданные на вход, 
          и предлагает выбор методов предобработки, подходящих для конкретного набора данных.
        </p>
        
        <h3>Основные возможности:</h3>
        <ul>
          <li>Загрузка файлов CSV и Excel</li>
          <li>Анализ структуры и качества данных</li>
          <li>Предобработка табличных данных и временных рядов</li>
          <li>Предпросмотр результатов и экспорт обработанных данных</li>
        </ul>
        
        <div class="action-buttons">
          <el-button type="primary" size="large" @click="startProcess">
            Начать работу
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
export default {
  name: 'HomeView',
  methods: {
    startProcess() {
      this.$router.push('/upload');
    }
  }
}
</script>

<style scoped>
.home {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
}

.welcome-card {
  width: 100%;
  max-width: 800px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-content {
  padding: 20px;
  font-size: 16px;
  line-height: 1.6;
}

.action-buttons {
  margin-top: 30px;
  display: flex;
  justify-content: center;
}

h3 {
  margin-top: 20px;
  margin-bottom: 10px;
}

ul {
  margin-bottom: 20px;
}

li {
  margin-bottom: 5px;
}
</style>