<template>
  <div class="data-upload">
    <h1>Data Upload</h1>

    <el-card class="upload-card">
      <div class="upload-area" @dragover.prevent @drop.prevent="onDrop">
        <el-upload
          class="upload-component"
          drag
          action="#"
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleFileChange"
        >
          <i class="el-icon-upload"></i>
          <div class="el-upload__text">
            Drag file here or <em>click to select</em>
          </div>
          <div class="el-upload__tip">
            CSV and Excel files up to 1 million rows are supported.
          </div>
        </el-upload>
      </div>

      <div v-if="selectedFile" class="file-info">
        <h3>Selected File: {{ selectedFile.name }}</h3>
        <p>Size: {{ formatFileSize(selectedFile.size) }}</p>
      </div>
    </el-card>

    <div class="action-buttons">
      <el-button
        type="primary"
        @click="uploadFile"
        :disabled="!selectedFile || isUploading"
      >
        <i class="el-icon-upload" v-if="!isUploading"></i>
        <i class="el-icon-loading" v-else></i>
        {{ isUploading ? "Uploading..." : "Upload" }}
      </el-button>
      <el-button @click="resetForm">Cancel</el-button>
    </div>

    <!-- Data Analysis Dialog -->
    <el-dialog
      title="Data Analysis"
      v-model="showAnalysisDialog"
      width="70%"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <div v-if="isAnalyzing">
        <div class="analysis-progress">
          <el-progress
            :percentage="analysisProgress"
            :format="progressFormat"
          ></el-progress>
          <p>{{ analysisStatus }}</p>
        </div>
      </div>
      <div v-else-if="analysisError">
        <el-alert
          title="Data Analysis Error"
          type="error"
          :description="analysisError"
          show-icon
        >
        </el-alert>
      </div>
      <div v-else-if="analysisResult">
        <h3>Analysis Completed Successfully</h3>
        <p>
          Rows: {{ analysisResult.row_count }}, Columns:
          {{ analysisResult.column_count }}
        </p>

        <h4>Recommended Preprocessing Methods:</h4>
        <el-tag
          v-for="method in analysisResult.recommended_methods"
          :key="method"
          class="method-tag"
        >
          {{ getMethodName(method) }}
        </el-tag>

        <el-table
          :data="analysisResult.columns"
          style="width: 100%; margin-top: 20px"
        >
          <el-table-column
            prop="name"
            label="Column Name"
            width="180"
          ></el-table-column>

          <el-table-column label="Data Type" width="180">
            <template #default="scope">
              <el-select
                v-model="scope.row.type"
                size="small"
                @change="updateColumnType(scope.row)"
              >
                <el-option label="Numeric" value="numeric"></el-option>
                <el-option label="Categorical" value="categorical"></el-option>
                <el-option label="Datetime" value="datetime"></el-option>
              </el-select>
            </template>
          </el-table-column>

          <el-table-column
            prop="missing_count"
            label="Missing"
            width="100"
          ></el-table-column>
          <el-table-column
            prop="unique_count"
            label="Unique"
            width="100"
          ></el-table-column>
          <el-table-column label="Statistics">
            <template #default="scope">
              <div v-if="scope.row.type === 'numeric'">
                Min: {{ scope.row.min_value?.toFixed(2) }}, Max:
                {{ scope.row.max_value?.toFixed(2) }}, Mean:
                {{ scope.row.mean_value?.toFixed(2) }}
              </div>
              <div v-else-if="scope.row.is_time_series">
                <el-tag size="small" type="success">Time Series</el-tag>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-divider v-if="analysisResult"></el-divider>

        <div v-if="analysisResult" class="target-selection">
          <h4>Select Target Variable:</h4>
          <div class="target-selection-content">
            <el-select
              v-model="selectedTargetColumn"
              placeholder="Select target variable"
              class="target-select"
            >
              <el-option
                v-for="column in analysisResult.columns"
                :key="column.name"
                :label="column.name"
                :value="column.name"
              >
                <span>{{ column.name }}</span>
                <span class="column-type">({{ column.type }})</span>
              </el-option>
            </el-select>

            <el-button
              type="primary"
              @click="setTargetColumn"
              :disabled="!selectedTargetColumn || settingTarget"
              :loading="settingTarget"
            >
              Set as Target
            </el-button>
          </div>

          <div v-if="targetSetSuccess" class="target-success">
            <el-alert
              title="Target variable has been set successfully."
              type="success"
              show-icon
              :closable="false"
            >
            </el-alert>
          </div>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAnalysisDialog = false" v-if="analysisError">
            Close
          </el-button>
          <el-button
            type="primary"
            @click="proceedToPreprocessing"
            v-if="analysisResult"
          >
            Proceed to Preprocessing
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { defineComponent, ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useStore } from "vuex";
import datasetService from "@/services/datasetService";
import { ElMessage } from "element-plus";

export default defineComponent({
  name: "DataUploadView",

  setup() {
    const router = useRouter();
    const store = useStore();

    // File state
    const selectedFile = ref(null);
    const isUploading = ref(false);

    // Analysis state
    const showAnalysisDialog = ref(false);
    const isAnalyzing = ref(false);
    const analysisProgress = ref(0);
    const analysisStatus = ref("");
    const analysisResult = ref(null);
    const analysisError = ref(null);

    // Target variable state
    const selectedTargetColumn = ref(null);
    const settingTarget = ref(false);
    const targetSetSuccess = ref(false);

    // --- File Handling ---
    const handleFileChange = (file) => {
      selectedFile.value = file.raw;
    };

    const onDrop = (e) => {
      e.preventDefault();
      if (e.dataTransfer.files.length > 0) {
        selectedFile.value = e.dataTransfer.files[0];
      }
    };

    const formatFileSize = (bytes) => {
      if (bytes === 0) return "0 Bytes";
      const k = 1024;
      const sizes = ["Bytes", "KB", "MB", "GB"];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    };

    const resetForm = () => {
      selectedFile.value = null;
      analysisResult.value = null;
      analysisError.value = null;
    };

    // --- Main Upload Logic ---
    const uploadFile = async () => {
      if (!selectedFile.value) return;

      try {
        isUploading.value = true;
        showAnalysisDialog.value = true;
        isAnalyzing.value = true;
        analysisStatus.value = "Uploading file...";
        analysisProgress.value = 10;

        const formData = new FormData();
        formData.append("file", selectedFile.value);

        analysisStatus.value = "Analyzing data...";
        analysisProgress.value = 40;

        const response = await datasetService.uploadDataset(formData);

        analysisStatus.value = "Finalizing analysis...";
        analysisProgress.value = 90;

        setTimeout(() => {
          analysisResult.value = response.data;
          analysisProgress.value = 100;
          isAnalyzing.value = false;
          store.commit("setDatasetId", response.data.dataset_id);
          store.commit("setDatasetInfo", response.data);
          ElMessage({
            message: "Data analysis completed successfully.",
            type: "success",
          });
        }, 500);
      } catch (error) {
        console.error("File upload error:", error);
        analysisError.value =
          error.response?.data?.detail || "An error occurred during upload.";
        isAnalyzing.value = false;
        ElMessage({ message: "File upload failed.", type: "error" });
      } finally {
        isUploading.value = false;
      }
    };

    // --- Analysis Dialog Logic ---
    const progressFormat = (percentage) =>
      percentage === 100 ? "Complete" : `${percentage}%`;

    const getMethodName = (methodId) => {
      const methodNames = {
        missing_values: "Handle Missing Values",
        outliers: "Handle Outliers",
        standardization: "Data Standardization",
        categorical_encoding: "Encode Categorical Variables",
        pca: "Dimensionality Reduction (PCA)",
        time_series_analysis: "Time Series Analysis",
        lagging: "Lagging Variables",
        rolling_statistics: "Rolling Statistics",
        date_components: "Extract Date Components",
      };
      return methodNames[methodId] || methodId;
    };

    const updateColumnType = (column) => {
      // This is a simplified local update. A more robust implementation
      // might involve an API call to re-validate on the backend.
      if (column.type === "datetime") {
        column.is_time_series = true; // Assume it could be a time series
      } else {
        column.is_time_series = false;
      }
      store.commit("setDatasetInfo", analysisResult.value);
      ElMessage.success(`Column type for "${column.name}" updated.`);
    };

    const setTargetColumn = async () => {
      if (!selectedTargetColumn.value || !analysisResult.value?.dataset_id)
        return;

      settingTarget.value = true;
      try {
        await datasetService.setTargetColumn(
          analysisResult.value.dataset_id,
          selectedTargetColumn.value
        );
        analysisResult.value.target_column = selectedTargetColumn.value;
        analysisResult.value.columns.forEach((col) => {
          col.is_target = col.name === selectedTargetColumn.value;
        });
        store.commit("setDatasetInfo", analysisResult.value);
        targetSetSuccess.value = true;
        ElMessage.success(
          `Variable "${selectedTargetColumn.value}" set as target.`
        );
      } catch (error) {
        console.error("Error setting target column:", error);
        ElMessage.error("Failed to set target variable.");
      } finally {
        settingTarget.value = false;
      }
    };

    const proceedToPreprocessing = () => {
      showAnalysisDialog.value = false;
      router.push("/preprocessing");
    };

    return {
      selectedFile,
      isUploading,
      showAnalysisDialog,
      isAnalyzing,
      analysisProgress,
      analysisStatus,
      analysisResult,
      analysisError,
      selectedTargetColumn,
      settingTarget,
      targetSetSuccess,
      handleFileChange,
      onDrop,
      formatFileSize,
      resetForm,
      uploadFile,
      proceedToPreprocessing,
      progressFormat,
      getMethodName,
      updateColumnType,
      setTargetColumn,
    };
  },
});
</script>

<style scoped>
.data-upload {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}
.upload-card {
  margin-top: 20px;
}
.upload-area {
  display: flex;
  justify-content: center;
  padding: 20px;
}
.file-info {
  margin-top: 20px;
  padding: 10px;
  background-color: #f0f9eb;
  border-radius: 4px;
}
.action-buttons {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.analysis-progress {
  text-align: center;
  padding: 20px;
}
.method-tag {
  margin-right: 10px;
  margin-bottom: 10px;
}
.target-selection {
  margin-top: 20px;
  padding: 15px;
  background-color: #f0f9ff;
  border-radius: 4px;
  border: 1px solid #e6f1fc;
}
.target-selection-content {
  display: flex;
  align-items: center;
  margin-top: 10px;
  margin-bottom: 15px;
}
.target-select {
  width: 300px;
  margin-right: 15px;
}
.column-type {
  margin-left: 10px;
  color: #909399;
}
.target-success {
  margin-top: 15px;
}
</style>