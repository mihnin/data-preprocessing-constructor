<template>
  <div class="header">
    <div class="header-content">
      <h1 class="title">Конструктор предобработки данных</h1>
      <div class="navigation-container">
        <div class="navigation">
          <el-steps :active="activeStep" finish-status="success" simple>
            <el-step title="Загрузка" icon="el-icon-upload"></el-step>
            <el-step title="Предобработка" icon="el-icon-s-operation"></el-step>
            <el-step title="Экспорт" icon="el-icon-download"></el-step>
          </el-steps>
        </div>
        <!-- Кнопка справки теперь внутри контейнера навигации -->
        <div class="help-button">
          <el-tooltip content="Руководство пользователя" placement="bottom">
            <el-button type="info" icon="el-icon-question" circle @click="goToHelp"></el-button>
          </el-tooltip>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AppHeader',
  computed: {
    activeStep() {
      const route = this.$route.path;
      if (route.includes('preview')) return 3;
      if (route.includes('preprocessing')) return 2;
      if (route.includes('upload')) return 1;
      return 0;
    }
  },
  methods: {
    goToHelp() {
      this.$router.push('/help');
    }
  }
}
</script>

<style scoped>
.header {
  background-color: #409eff;
  color: white;
  padding: 15px 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
}

.title {
  margin: 0;
  padding: 0;
  font-size: 24px;
  margin-bottom: 15px;
}

.navigation-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: white;
  padding: 15px;
  border-radius: 4px;
}

.navigation {
  flex-grow: 1;
}

.help-button {
  margin-left: 15px;
}

@media (max-width: 768px) {
  .navigation-container {
    flex-direction: column;
  }
  
  .help-button {
    margin-left: 0;
    margin-top: 10px;
    align-self: flex-end;
  }
}
</style>