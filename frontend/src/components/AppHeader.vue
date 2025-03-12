<template>
  <div class="header">
    <div class="header-content">
      <h1 class="title">Конструктор предобработки данных</h1>
      <div class="navigation">
        <el-steps :active="activeStep" finish-status="success" simple>
          <el-step title="Загрузка" icon="el-icon-upload"></el-step>
          <el-step title="Предобработка" icon="el-icon-s-operation"></el-step>
          <el-step title="Экспорт" icon="el-icon-download"></el-step>
        </el-steps>
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
  }
}
</script>

<style scoped>
.header {
  background-color: #409eff;
  color: white;
  padding: 15px 20px;
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

.navigation {
  background-color: white;
  padding: 15px;
  border-radius: 4px;
}
</style>
