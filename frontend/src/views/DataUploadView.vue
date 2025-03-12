<template>
  <div class="data-upload">
    <h1>Загрузка данных</h1>
    
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
            Перетащите файл сюда или <em>нажмите для выбора</em>
          </div>
          <div class="el-upload__tip">
            Поддерживаются файлы CSV и Excel до 1 млн строк
          </div>
        </el-upload>
      </div>

      <div v-if="selectedFile" class="file-info">
        <h3>Выбранный файл: {{ selectedFile.name }}</h3>
        <p>Размер: {{ formatFileSize(selectedFile.size) }}</p>
      </div>
      
      <div class="upload-options" v-if="selectedFile">
        <h3>Параметры загрузки</h3>
        
        <el-form label-width="150px">
          <el-form-item label="Разделитель (CSV):" v-if="isCSV">
            <el-select v-model="delimiter" placeholder="Выберите разделитель">
              <el-option label="Запятая (,)" value="," />
              <el-option label="Точка с запятой (;)" value=";" />
              <el-option label="Табуляция" value="\t" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="Кодировка:">
            <el-select v-model="encoding" placeholder="Выберите кодировку">
              <el-option label="UTF-8" value="utf-8" />
              <el-option label="Windows-1251" value="windows-1251" />
              <el-option label="ISO-8859-1" value="iso-8859-1" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="Заголовки:">
            <el-checkbox v-model="hasHeader">Первая строка содержит заголовки</el-checkbox>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
    
    <div class="action-buttons">
      <el-button type="primary" @click="uploadFile" :disabled="!selectedFile || isUploading">
        <i class="el-icon-upload" v-if="!isUploading"></i>
        <i class="el-icon-loading" v-else></i>
        {{ isUploading ? 'Загрузка...' : 'Загрузить' }}
      </el-button>
      <el-button @click="resetForm">Отмена</el-button>
    </div>
    
    <!-- Отображение прогресса загрузки и анализа -->
    <el-dialog
      title="Анализ данных"
      v-model="showAnalysisDialog"
      width="70%"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <div v-if="isAnalyzing">
        <div class="analysis-progress">
          <el-progress :percentage="analysisProgress" :format="progressFormat"></el-progress>
          <p>{{ analysisStatus }}</p>
        </div>
      </div>
      <div v-else-if="analysisError">
        <el-alert
          title="Ошибка анализа данных"
          type="error"
          :description="analysisError"
          show-icon
        >
        </el-alert>
      </div>
      <div v-else-if="analysisResult">
        <h3>Анализ успешно завершен</h3>
        <p>Строк: {{ analysisResult.row_count }}, Столбцов: {{ analysisResult.column_count }}</p>
        
        <h4>Рекомендуемые методы предобработки:</h4>
        <el-tag 
          v-for="method in analysisResult.recommended_methods" 
          :key="method"
          class="method-tag"
        >
          {{ getMethodName(method) }}
        </el-tag>
        
        <el-table :data="analysisResult.columns" style="width: 100%; margin-top: 20px;">
          <el-table-column prop="name" label="Название столбца" width="180"></el-table-column>
          <el-table-column prop="type" label="Тип данных" width="120"></el-table-column>
          <el-table-column prop="missing_count" label="Пропуски" width="100"></el-table-column>
          <el-table-column prop="unique_count" label="Уникальные" width="100"></el-table-column>
          <el-table-column label="Статистика">
            <template #default="scope">
              <div v-if="scope.row.type === 'numeric'">
                Мин: {{ scope.row.min_value?.toFixed(2) }}, 
                Макс: {{ scope.row.max_value?.toFixed(2) }}, 
                Среднее: {{ scope.row.mean_value?.toFixed(2) }}
              </div>
              <div v-else-if="scope.row.is_time_series">
                <el-tag size="small" type="success">Временной ряд</el-tag>
              </div>
            </template>
          </el-table-column>
        </el-table>
        
        <el-divider v-if="analysisResult"></el-divider>

        <div v-if="analysisResult" class="target-selection">
          <h4>Выберите целевую переменную:</h4>
          <div class="target-selection-content">
            <el-select 
              v-model="selectedTargetColumn" 
              placeholder="Выберите целевую переменную"
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
              Установить как целевую
            </el-button>
          </div>
          
          <div v-if="targetSetSuccess" class="target-success">
            <el-alert
              title="Целевая переменная успешно установлена"
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
          <el-button @click="showAnalysisDialog = false" v-if="analysisError">Закрыть</el-button>
          <el-button type="primary" @click="proceedToPreprocessing" v-if="analysisResult">
            Перейти к предобработке
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { defineComponent, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useStore } from 'vuex';
import datasetService from '@/services/datasetService';
import { ElMessage } from 'element-plus';

export default defineComponent({
  name: 'DataUploadView',
  
  setup() {
    const router = useRouter();
    const store = useStore();
    
    // Состояние файла
    const selectedFile = ref(null);
    const isCSV = computed(() => {
      if (!selectedFile.value) return false;
      return selectedFile.value.name.toLowerCase().endsWith('.csv');
    });
    
    // Параметры загрузки
    const delimiter = ref(',');
    const encoding = ref('utf-8');
    const hasHeader = ref(true);
    
    // Состояние загрузки
    const isUploading = ref(false);
    const uploadProgress = ref(0);
    
    // Состояние анализа
    const showAnalysisDialog = ref(false);
    const isAnalyzing = ref(false);
    const analysisProgress = ref(0);
    const analysisStatus = ref('');
    const analysisResult = ref(null);
    const analysisError = ref(null);
    
    // Методы обработки файла
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
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };
    
    const resetForm = () => {
      selectedFile.value = null;
      delimiter.value = ',';
      encoding.value = 'utf-8';
      hasHeader.value = true;
      uploadProgress.value = 0;
      analysisResult.value = null;
      analysisError.value = null;
    };
    
    const progressFormat = (percentage) => {
      return percentage === 100 ? 'Завершено' : `${percentage}%`;
    };
    
    // Функция загрузки файла
    const uploadFile = async () => {
      if (!selectedFile.value) return;
      
      try {
        isUploading.value = true;
        showAnalysisDialog.value = true;
        isAnalyzing.value = true;
        analysisStatus.value = 'Загрузка файла...';
        analysisProgress.value = 10;
        
        // Создаем FormData для загрузки файла
        const formData = new FormData();
        formData.append('file', selectedFile.value);
        
        // Добавляем параметры
        if (isCSV.value) {
          formData.append('delimiter', delimiter.value);
        }
        formData.append('encoding', encoding.value);
        formData.append('has_header', hasHeader.value);
        
        // Загружаем файл и получаем анализ
        analysisStatus.value = 'Анализ данных...';
        analysisProgress.value = 40;
        
        const response = await datasetService.uploadDataset(formData);
        
        analysisStatus.value = 'Завершение анализа...';
        analysisProgress.value = 90;
        
        // Небольшая задержка для лучшего UX
        setTimeout(() => {
          analysisResult.value = response.data;
          analysisProgress.value = 100;
          isAnalyzing.value = false;
          
          // Сохраняем ID набора данных в хранилище
          store.commit('setDatasetId', response.data.dataset_id);
          store.commit('setDatasetInfo', response.data);
          
          ElMessage({
            message: 'Анализ данных успешно завершен',
            type: 'success'
          });
        }, 500);
        
      } catch (error) {
        console.error('Ошибка загрузки файла:', error);
        analysisError.value = error.response?.data?.detail || 'Произошла ошибка при загрузке файла';
        isAnalyzing.value = false;
        
        ElMessage({
          message: 'Ошибка загрузки файла',
          type: 'error'
        });
      } finally {
        isUploading.value = false;
      }
    };
    
    // Переход к следующему шагу
    const proceedToPreprocessing = () => {
      showAnalysisDialog.value = false;
      router.push('/preprocessing');
    };
    
    // Получение названия метода предобработки
    const getMethodName = (methodId) => {
      const methodNames = {
        'missing_values': 'Обработка пропущенных значений',
        'outliers': 'Обработка выбросов',
        'standardization': 'Стандартизация данных',
        'categorical_encoding': 'Кодирование категориальных переменных',
        'pca': 'Снижение размерности (PCA)',
        'time_series_analysis': 'Анализ временных рядов',
        'lagging': 'Лагирование переменных',
        'rolling_statistics': 'Скользящие статистики'
      };
      
      return methodNames[methodId] || methodId;
    };
    
    // Состояние выбора целевой переменной
    const selectedTargetColumn = ref(null);
    const settingTarget = ref(false);
    const targetSetSuccess = ref(false);

    // Функция установки целевой переменной
    const setTargetColumn = async () => {
      if (!selectedTargetColumn.value || !analysisResult.value?.dataset_id) return;
      
      settingTarget.value = true;
      try {
        // Вызов API для установки целевой переменной
        await datasetService.setTargetColumn(
          analysisResult.value.dataset_id, 
          selectedTargetColumn.value
        );
        
        // Обновляем статус в локальных данных
        analysisResult.value.target_column = selectedTargetColumn.value;
        
        // Обновляем статус is_target во всех колонках
        analysisResult.value.columns.forEach(col => {
          col.is_target = col.name === selectedTargetColumn.value;
        });
        
        // Сохраняем обновленные данные в хранилище
        store.commit('setDatasetInfo', analysisResult.value);
        
        targetSetSuccess.value = true;
        
        ElMessage({
          message: `Переменная "${selectedTargetColumn.value}" установлена как целевая`,
          type: 'success'
        });
      } catch (error) {
        console.error('Ошибка установки целевой переменной:', error);
        ElMessage.error('Не удалось установить целевую переменную');
      } finally {
        settingTarget.value = false;
      }
    };
    
    return {
      selectedFile,
      isCSV,
      delimiter,
      encoding,
      hasHeader,
      isUploading,
      uploadProgress,
      showAnalysisDialog,
      isAnalyzing,
      analysisProgress,
      analysisStatus,
      analysisResult,
      analysisError,
      handleFileChange,
      onDrop,
      formatFileSize,
      resetForm,
      uploadFile,
      proceedToPreprocessing,
      progressFormat,
      getMethodName,
      selectedTargetColumn,
      settingTarget,
      targetSetSuccess,
      setTargetColumn
    };
  }
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

.upload-options {
  margin-top: 20px;
  padding: 10px;
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