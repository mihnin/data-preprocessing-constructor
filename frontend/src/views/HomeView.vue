<template>
  <div class="home">
    <el-card class="welcome-card">
      <template #header>
        <div class="card-header">
          <h2>Welcome to the Data Preprocessing Builder</h2>
        </div>
      </template>
      <div class="card-content">
        <p>
          This is a tool for analyzing and preprocessing datasets. The system
          analyzes the input data and suggests a selection of preprocessing
          methods suitable for the specific dataset.
        </p>

        <h3>Key Features:</h3>
        <ul>
          <li>Upload CSV and Excel files</li>
          <li>Analyze data structure and quality</li>
          <li>Preprocess tabular data and time series</li>
          <li>Preview results and export processed data</li>
        </ul>

        <div class="action-buttons">
          <el-button type="primary" size="large" @click="startProcess">
            Get Started
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script>
export default {
  name: "HomeView",
  methods: {
    startProcess() {
      this.$router.push("/upload");
    },
  },
};
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