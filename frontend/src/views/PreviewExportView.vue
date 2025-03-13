<template>
  <div class="preview-export-view">
    <h1>Результаты предобработки</h1>
    
    <el-alert
      v-if="!resultId"
      title="Нет доступных результатов"
      type="warning"
      description="Для доступа к этой странице необходимо сначала выполнить предобработку данных"
      show-icon
      :closable="false"
    >
      <template #default>
        <el-button type="primary" size="small" @click="goToPreprocessing">
          К выбору методов предобработки
        </el-button>
      </template>
    </el-alert>
    
    <template v-if="resultId">
      <!-- Индикатор прогресса обработки -->
      <el-card v-if="processingStatus === 'processing'" class="processing-card">
        <div class="processing-indicator">
          <el-progress 
            type="circle" 
            :percentage="processingProgress.percent || 0" 
            :status="processingProgress.percent < 100 ? 'exception' : 'success'"
          ></el-progress>
          <h3>{{ getProcessingStageTitle(processingProgress.stage) }}</h3>
          <p v-if="processingProgress.method_name">
            Выполняется: {{ processingProgress.method_name }}
          </p>
          <p>Это может занять некоторое время в зависимости от размера данных и выбранных методов.</p>
          <el-button type="primary" plain @click="checkStatus">
            Обновить статус
          </el-button>
        </div>
      </el-card>
      
      <!-- Сообщение об ошибке -->
      <el-card v-else-if="processingStatus === 'error'" class="error-card">
        <div class="error-message">
          <i class="el-icon-error" style="font-size: 48px; color: #F56C6C;"></i>
          <h3>Произошла ошибка при обработке данных</h3>
          <p>{{ errorMessage }}</p>
          <el-button type="primary" @click="goToPreprocessing">
            Вернуться к настройке предобработки
          </el-button>
        </div>
      </el-card>
      
      <!-- Результаты предобработки -->
      <div v-else-if="processingStatus === 'completed' && resultMetadata" class="result-container">
        <el-card class="result-summary">
          <template #header>
            <div class="card-header">
              <span>Сводка результатов предобработки</span>
            </div>
          </template>
          
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Количество строк">
              {{ resultMetadata.row_count }}
            </el-descriptions-item>
            <el-descriptions-item label="Количество столбцов">
              {{ resultMetadata.column_count }}
            </el-descriptions-item>
            <el-descriptions-item label="ID набора данных">
              {{ resultMetadata.dataset_id }}
            </el-descriptions-item>
            <el-descriptions-item label="ID результата">
              {{ resultMetadata.result_id }}
            </el-descriptions-item>
          </el-descriptions>
          
          <h3>Применённые методы предобработки</h3>
          
          <el-table :data="appliedMethods" style="width: 100%" border>
            <el-table-column prop="name" label="Метод"></el-table-column>
            <el-table-column label="Параметры">
              <template #default="scope">
                <div v-for="(value, key) in scope.row.parameters" :key="key">
                  <strong>{{ formatParameterName(key) }}:</strong> {{ formatParameterValue(key, value) }}
                </div>
              </template>
            </el-table-column>
          </el-table>
          
          <h3>Столбцы в обработанных данных</h3>
          <el-tag
            v-for="column in resultMetadata.columns"
            :key="column"
            :type="isNewColumn(column) ? 'success' : ''"
            class="column-tag"
          >
            {{ column }}
          </el-tag>
        </el-card>
        
        <!-- Добавляем компонент для управления метаданными масштабирования -->
        <el-card v-if="hasScalingParams" class="metadata-card">
          <template #header>
            <div class="card-header">
              <span>Управление параметрами масштабирования</span>
            </div>
          </template>
          
          <ScalingMetadataManager
            :result-id="resultId"
            :has-scaling-params="hasScalingParams"
            :scaling-method-name="scalingMethodName"
            :available-columns="resultMetadata.columns || []"
            :scaling-params="scalingParams"
            @metadata-updated="onMetadataUpdated"
            @inverse-scaling-applied="onInverseScalingApplied"
          />
        </el-card>
        
        <el-card class="data-preview">
          <template #header>
            <div class="card-header">
              <span>Предпросмотр данных</span>
              <div class="header-actions">
                <el-button 
                  type="primary" 
                  @click="loadDataPreview" 
                  :loading="isPreviewLoading"
                  size="small"
                >
                  Обновить данные
                </el-button>
                <el-dropdown @command="handleColumnVisibility" trigger="click">
                  <el-button type="info" size="small" plain>
                    Видимость столбцов <i class="el-icon-arrow-down"></i>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="show-all">Показать все</el-dropdown-item>
                      <el-dropdown-item command="hide-all">Скрыть все</el-dropdown-item>
                      <el-dropdown-item divided></el-dropdown-item>
                      <el-dropdown-item 
                        v-for="column in resultMetadata.columns" 
                        :key="column"
                        :command="`toggle-${column}`"
                      >
                        <el-checkbox 
                          v-model="visibleColumns[column]" 
                          @click.stop
                        >
                          {{ column }}
                        </el-checkbox>
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </template>
          
          <!-- Fix for the spinner component -->
          <div v-if="isPreviewLoading" class="preview-loading">
            <el-icon class="is-loading"><loading /></el-icon>
            <p>Загрузка данных...</p>
          </div>
          
          <div v-else-if="previewError" class="preview-error">
            <el-alert type="error" :closable="false">
              {{ previewError }}
            </el-alert>
          </div>
          
          <div v-else-if="previewData && previewData.length > 0" class="preview-content">
            <!-- Улучшенная таблица с расширенными возможностями -->
            <el-table
              :data="previewData"
              border
              style="width: 100%"
              max-height="400"
              :default-sort="{ prop: defaultSortColumn, order: 'ascending' }"
              @sort-change="handleSortChange"
              @header-dragend="handleColumnDrag"
              v-loading="tableLoading"
            >
              <!-- Динамические столбцы на основе видимости -->
              <el-table-column
                v-for="column in visibleColumnsList"
                :key="column"
                :prop="column"
                :label="column"
                min-width="150"
                sortable
                :filters="getColumnFilters(column)"
                :filter-method="filterColumn"
                filter-placement="bottom"
                :class="{ 'highlight-column': highlightedColumn === column }"
              >
                <template #header>
                  <div class="column-header">
                    {{ column }}
                    <i 
                      class="el-icon-search" 
                      @click.stop="openFilterDialog(column)"
                      title="Расширенная фильтрация"
                    ></i>
                  </div>
                </template>
              </el-table-column>
            </el-table>
            
            <!-- Панель пагинации -->
            <div class="pagination-controls">
              <el-pagination
                :page-size="pageSize"
                :current-page="currentPage"
                :total="totalRecords"
                layout="total, sizes, prev, pager, next"
                :page-sizes="[10, 20, 50, 100]"
                @size-change="handleSizeChange"
                @current-change="handleCurrentChange"
              >
              </el-pagination>
            </div>
          </div>
          
          <div v-else class="no-preview">
            <p>Нажмите кнопку "Загрузить предпросмотр" для просмотра обработанных данных</p>
          </div>
        </el-card>
        
        <!-- Диалог расширенной фильтрации -->
        <el-dialog
          v-model="filterDialogVisible"
          :title="`Фильтрация столбца: ${currentFilterColumn}`"
          width="50%"
        >
          <el-form>
            <el-form-item label="Тип фильтра">
              <el-select v-model="filterType" placeholder="Выберите тип фильтра">
                <el-option label="Содержит" value="contains"></el-option>
                <el-option label="Равно" value="equals"></el-option>
                <el-option label="Больше" value="greater"></el-option>
                <el-option label="Меньше" value="less"></el-option>
                <el-option label="Диапазон" value="range"></el-option>
              </el-select>
            </el-form-item>
            
            <template v-if="filterType !== 'range'">
              <el-form-item label="Значение">
                <el-input v-model="filterValue" placeholder="Введите значение"></el-input>
              </el-form-item>
            </template>
            
            <template v-else>
              <el-form-item label="От">
                <el-input v-model="filterRangeMin" placeholder="Минимальное значение"></el-input>
              </el-form-item>
              <el-form-item label="До">
                <el-input v-model="filterRangeMax" placeholder="Максимальное значение"></el-input>
              </el-form-item>
            </template>
          </el-form>
          
          <template #footer>
            <el-button @click="filterDialogVisible = false">Отмена</el-button>
            <el-button type="primary" @click="applyAdvancedFilter">Применить</el-button>
          </template>
        </el-dialog>
        
        <el-card class="export-card">
          <template #header>
            <div class="card-header">
              <span>Экспорт обработанных данных</span>
            </div>
          </template>
          <el-form label-width="200px">
            <el-form-item label="Формат экспорта:">
              <el-radio-group v-model="exportFormat">
                <el-radio label="csv">CSV</el-radio>
                <el-radio label="excel">Excel</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="Параметры CSV:" v-if="exportFormat === 'csv'">
              <el-select v-model="csvDelimiter" placeholder="Разделитель" style="width: 150px">
                <el-option label="Запятая (,)" value="," />
                <el-option label="Точка с запятой (;)" value=";" />
                <el-option label="Табуляция" value="\t" />
              </el-select>
            </el-form-item>
          </el-form>
          <el-button 
            type="success" 
            icon="el-icon-download" 
            @click="exportData"
            :loading="isExporting"
          >
            Экспортировать данные
          </el-button>
        </el-card>
        
        <div class="navigation-buttons">
          <el-button @click="goToPreprocessing">Назад</el-button>
          <el-button type="primary" @click="finishProcess">Завершить</el-button>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
import { defineComponent, ref, computed, reactive, onMounted, watch, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useStore } from 'vuex';
import { ElMessage } from 'element-plus';
import preprocessingService from '@/services/preprocessingService';
import datasetService from '@/services/datasetService';
import ScalingMetadataManager from '@/components/ScalingMetadataManager.vue';

export default defineComponent({
  name: 'PreviewExportView',
  components: {
    ScalingMetadataManager
  },
  setup() {
    const router = useRouter();
    const store = useStore();
    
    // Состояние результата
    const resultId = computed(() => store.state.resultId);
    const processingStatus = ref('processing'); // processing, error, completed
    const errorMessage = ref('');
    const resultMetadata = ref(null);
    
    // Информация о прогрессе обработки
    const processingProgress = ref({
      percent: 0,
      stage: 'preparing',
      method_name: null
    });
    
    // Добавляем переменную для хранения интервала
    const statusInterval = ref(null);
    
    // Состояние предпросмотра
    const isPreviewLoading = ref(false);
    const previewData = ref(null);
    const previewError = ref(null);
    const originalColumns = ref([]);
    
    // Состояние экспорта
    const exportFormat = ref('csv');
    const csvDelimiter = ref(',');
    const isExporting = ref(false);
    
    // Запуск периодического опроса статуса
    const startStatusPolling = () => {
      // Проверяем статус каждые 3 секунды
      statusInterval.value = setInterval(() => {
        checkStatus();
      }, 3000);
    };
    
    // Останавливаем опрос при размонтировании компонента
    onUnmounted(() => {
      if (statusInterval.value) {
        clearInterval(statusInterval.value);
      }
    });
    
    // Получение статуса обработки
    onMounted(() => {
      if (resultId.value) {
        checkStatus();
        startStatusPolling(); // Запускаем автоматический опрос
      }
    });
    
    // Проверка статуса обработки
    const checkStatus = async () => {
      if (!resultId.value) return;
      
      try {
        const response = await preprocessingService.getPreprocessingStatus(resultId.value);
        
        if (response.data.status === 'error') {
          processingStatus.value = 'error';
          errorMessage.value = response.data.message;
          // Останавливаем опрос при ошибке
          if (statusInterval.value) {
            clearInterval(statusInterval.value);
          }
        } else if (response.data.status === 'completed') {
          processingStatus.value = 'completed';
          resultMetadata.value = response.data.metadata;
          // Останавливаем опрос при завершении
          if (statusInterval.value) {
            clearInterval(statusInterval.value);
          }
          // Получение оригинальных столбцов из метаданных датасета
          try {
            const datasetResponse = await datasetService.getDatasetInfo(resultMetadata.value.dataset_id);
            originalColumns.value = datasetResponse.data.columns.map(col => col.name);
          } catch (error) {
            console.error('Ошибка получения исходных столбцов:', error);
          }
        } else {
          processingStatus.value = 'processing';
          // Обновляем информацию о прогрессе, если она доступна
          if (response.data.progress) {
            processingProgress.value = response.data.progress;
          }
        }
      } catch (error) {
        console.error('Ошибка проверки статуса:', error);
        processingStatus.value = 'error';
        errorMessage.value = 'Не удалось получить статус обработки';
        // Останавливаем опрос при ошибке
        if (statusInterval.value) {
          clearInterval(statusInterval.value);
        }
      }
    };
    
    // Экспорт данных
    const exportData = async () => {
      if (!resultId.value) return;
      
      isExporting.value = true;
      
      try {
        // Запрос для экспорта данных с учетом выбранного формата
        const response = await preprocessingService.exportDataset(resultId.value, exportFormat.value);
        // Создание ссылки для скачивания
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        // Устанавливаем правильное расширение файла
        const fileExtension = exportFormat.value === 'excel' ? 'xlsx' : 'csv';
        link.setAttribute('download', `processed_data_${resultId.value}.${fileExtension}`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        ElMessage({
          message: 'Данные успешно экспортированы',
          type: 'success'
        });
      } catch (error) {
        console.error('Ошибка экспорта данных:', error);
        ElMessage.error('Не удалось экспортировать данные');
      } finally {
        isExporting.value = false;
      }
    };
    
    // Проверка, является ли столбец новым
    const isNewColumn = (column) => {
      return originalColumns.value.length > 0 && !originalColumns.value.includes(column);
    };
    
    // Применённые методы
    const appliedMethods = computed(() => {
      if (!resultMetadata.value || !resultMetadata.value.config || !resultMetadata.value.config.methods) {
        return [];
      }
      return resultMetadata.value.config.methods.map(method => {
        // Получение информации о методе из метаданных
        return {
          name: getMethodName(method.method_id),
          parameters: method.parameters || {}
        };
      });
    });
    
    // Получение названия метода
    const getMethodName = (methodId) => {
      const methodNames = {
        'missing_values': 'Обработка пропущенных значений',
        'outliers': 'Обработка выбросов',
        'standardization': 'Стандартизация данных',
        'categorical_encoding': 'Кодирование категориальных переменных',
        'pca': 'Снижение размерности (PCA)',
        'time_series_analysis': 'Анализ временных рядов',
        'lagging': 'Лагирование переменных',
        'rolling_statistics': 'Скользящие статистики',
        'date_components': 'Извлечение компонентов даты'
      };
      return methodNames[methodId] || methodId;
    };
    
    // Форматирование названия параметра
    const formatParameterName = (paramName) => {
      const paramNames = {
        'strategy': 'Стратегия',
        'columns': 'Столбцы',
        'threshold': 'Порог',
        'target_column': 'Целевая переменная',
        'lag_periods': 'Периоды лагирования',
        'exog_columns': 'Экзогенные переменные',
        'window_size': 'Размер окна',
        'statistics': 'Статистики',
        'n_components': 'Количество компонент',
        'components': 'Компоненты даты'
      };
      return paramNames[paramName] || paramName;
    };
    
    // Форматирование значения параметра
    const formatParameterValue = (paramName, value) => {
      if (paramName === 'strategy') {
        const strategyLabels = {
          'mean': 'Заполнить средним',
          'median': 'Заполнить медианой',
          'mode': 'Заполнить модой',
          'drop_rows': 'Удалить строки',
          'zscore': 'Z-оценка',
          'iqr': 'Межквартильный размах',
          'standard': 'Стандартизация',
          'minmax': 'Мин-макс нормализация',
          'onehot': 'One-Hot кодирование',
          'label': 'Label кодирование'
        };
        return strategyLabels[value] || value;
      }
      // Добавляем форматирование для компонентов даты
      if (paramName === 'components') {
        if (Array.isArray(value)) {
          // Преобразуем идентификаторы компонентов в удобочитаемые названия
          const componentLabels = {
            'year': 'Год',
            'month': 'Месяц',
            'quarter': 'Квартал',
            'day_of_week': 'День недели',
            'day_of_month': 'День месяца',
            'day_of_year': 'День года',
            'week_of_year': 'Неделя года'
          };
          return value.map(component => componentLabels[component] || component).join(', ');
        }
      }
      if (Array.isArray(value)) {
        return value.length > 0 ? value.join(', ') : 'Не выбрано';
      }
      return value === null || value === undefined ? 'Не указано' : value;
    };
    
    // Получение заголовка для текущего этапа обработки
    const getProcessingStageTitle = (stage) => {
      const stageTitles = {
        'preparing': 'Подготовка к обработке...',
        'loading': 'Загрузка данных...',
        'preprocessing': 'Инициализация предобработки...',
        'processing_method': 'Выполнение предобработки...',
        'saving': 'Сохранение результатов...',
        'completed': 'Обработка завершена',
        'error': 'Ошибка при обработке'
      };
      return stageTitles[stage] || 'Выполняется обработка данных...';
    };
    
    // Навигация
    const goToPreprocessing = () => {
      router.push('/preprocessing');
    };
    
    const finishProcess = () => {
      // Очистка состояния
      store.commit('clearPreprocessingState');
      router.push('/');
    };
    
    // Проверка наличия параметров масштабирования
    const hasScalingParams = computed(() => {
      // Проверяем прямое наличие scaling_params в метаданных
      if (resultMetadata.value && resultMetadata.value.scaling_params) {
        return true;
      }
      // Проверяем наличие методов масштабирования в примененных методах
      if (resultMetadata.value && resultMetadata.value.config && resultMetadata.value.config.methods) {
        return resultMetadata.value.config.methods.some(method => 
          ['standardization', 'minmax_scaling', 'normalization'].includes(method.method_id)
        );
      }
      return false;
    });
    
    // Получение названия метода масштабирования
    const scalingMethodName = computed(() => {
      if (!resultMetadata.value || !resultMetadata.value.config || !resultMetadata.value.config.methods) {
        return '';
      }
      const scalingMethod = resultMetadata.value.config.methods.find(method => 
        ['standardization', 'minmax_scaling', 'normalization'].includes(method.method_id)
      );
      if (!scalingMethod) return '';
      
      const methodNames = {
        'standardization': 'Стандартизация',
        'minmax_scaling': 'Мин-макс нормализация',
        'normalization': 'Нормализация'
      };
      return methodNames[scalingMethod.method_id] || scalingMethod.method_id;
    });
    
    // Обработчик события обновления метаданных
    const onMetadataUpdated = (scalingParams) => {
      console.log('Обновление параметров масштабирования:', scalingParams);
      // Обновляем метаданные результата, добавляя информацию о масштабировании
      if (resultMetadata.value) {
        if (!resultMetadata.value.scaling_params) {
          resultMetadata.value = {
            ...resultMetadata.value,
            scaling_params: scalingParams
          };
        } else {
          resultMetadata.value.scaling_params = scalingParams;
        }
        // Важно! Сохраняем параметры масштабирования в хранилище
        store.dispatch('setScalingParams', scalingParams);
      }
      // Обновляем предпросмотр данных, если он загружен
      if (previewData.value) {
        loadDataPreview();
      }
      ElMessage({
        message: 'Параметры масштабирования обновлены',
        type: 'success',
      });
    };
    
    // Обработчик события применения обратного масштабирования
    const onInverseScalingApplied = (data) => {
      console.log('Результат обратного масштабирования:', data);
      
      // Обновляем ID результата
      if (data && data.result_id) {
        store.dispatch('setResult', data.result_id);
        // Обновляем текущий resultId для обновления представления
        resultId.value = data.result_id;
        // Сбрасываем состояние и перезагружаем данные
        checkStatus();
      }
      
      ElMessage({
        message: 'Обратное масштабирование успешно применено. Результаты обновлены.',
        type: 'success',
        duration: 5000
      });
    };
    
    // Получение параметров масштабирования
    const scalingParams = computed(() => {
      // Первый вариант - брать из метаданных результата
      if (resultMetadata.value && resultMetadata.value.scaling_params) {
        return resultMetadata.value.scaling_params;
      }
      // Второй вариант - брать из хранилища
      return store.state.scalingParams;
    });
    
    // Состояние таблицы данных
    const visibleColumns = reactive({});
    const defaultSortColumn = ref('');
    const currentSortColumn = ref('');
    const currentSortOrder = ref('ascending');
    const tableLoading = ref(false);
    const highlightedColumn = ref('');
    
    // Пагинация
    const pageSize = ref(20);
    const currentPage = ref(1);
    const totalRecords = ref(0);
    
    // Фильтрация
    const filterDialogVisible = ref(false);
    const currentFilterColumn = ref('');
    const filterType = ref('contains');
    const filterValue = ref('');
    const filterRangeMin = ref('');
    const filterRangeMax = ref('');
    const activeFilters = reactive({});
    
    // Вычисляемые свойства
    const visibleColumnsList = computed(() => {
      if (!resultMetadata.value || !resultMetadata.value.columns || !Array.isArray(resultMetadata.value.columns)) {
        return [];
      }
      return resultMetadata.value.columns.filter(col => visibleColumns[col] !== false);
    });
    
    // Инициализация состояния видимости столбцов
    watch(() => resultMetadata.value?.columns, (newColumns) => {
      if (newColumns) {
        // По умолчанию все столбцы видимы
        newColumns.forEach(col => {
          if (visibleColumns[col] === undefined) {
            visibleColumns[col] = true;
          }
        });
        // Устанавливаем первый столбец как столбец сортировки по умолчанию
        if (newColumns.length > 0 && !defaultSortColumn.value) {
          defaultSortColumn.value = newColumns[0];
        }
      }
    }, { immediate: true });
    
    // Функции-обработчики
    const handleColumnVisibility = (command) => {
      if (command === 'show-all') {
        resultMetadata.value.columns.forEach(col => {
          visibleColumns[col] = true;
        });
      } else if (command === 'hide-all') {
        resultMetadata.value.columns.forEach(col => {
          visibleColumns[col] = false;
        });
      } else if (command.startsWith('toggle-')) {
        const column = command.replace('toggle-', '');
        visibleColumns[column] = !visibleColumns[column];
      }
    };
    
    const handleSortChange = ({ prop, order }) => {
      currentSortColumn.value = prop;
      currentSortOrder.value = order;
      reloadFilteredData();
    };
    
    const handleColumnDrag = (newWidth, oldWidth, column) => {
      // Обработка перетаскивания столбцов для изменения их ширины
      console.log(`Column ${column.label} resized from ${oldWidth} to ${newWidth}`);
    };
    
    const getColumnFilters = (column) => {
      // Генерация фильтров для столбца на основе данных
      if (!previewData.value || previewData.value.length === 0) return [];
      // Получаем уникальные значения для столбца
      const uniqueValues = [...new Set(previewData.value
        .map(row => row[column])
        .filter(val => val !== null && val !== undefined))];
      
      // Возвращаем массив объектов для фильтра
      return uniqueValues.slice(0, 10).map(value => ({
        text: String(value),
        value: value
      }));
    };
    
    const filterColumn = (value, row, column) => {
      // Стандартная функция фильтрации для el-table
      const cellValue = row[column.property];
      if (cellValue === undefined || cellValue === null) return false;
      return String(cellValue).toLowerCase().includes(String(value).toLowerCase());
    };
    
    const openFilterDialog = (column) => {
      currentFilterColumn.value = column;
      // Сбрасываем значения фильтра
      filterType.value = 'contains';
      filterValue.value = '';
      filterRangeMin.value = '';
      filterRangeMax.value = '';
      filterDialogVisible.value = true;
    };
    
    const applyAdvancedFilter = () => {
      // Сохраняем настройки фильтра
      activeFilters[currentFilterColumn.value] = {
        type: filterType.value,
        value: filterValue.value,
        rangeMin: filterRangeMin.value,
        rangeMax: filterRangeMax.value
      };
      filterDialogVisible.value = false;
      
      // Применяем фильтр к данным
      reloadFilteredData();
      // Подсвечиваем отфильтрованный столбец
      highlightedColumn.value = currentFilterColumn.value;
    };
    
    const reloadFilteredData = () => {
      // Перезагружаем данные с учетом фильтров и сортировки
      tableLoading.value = true;
      // Здесь вы можете добавить логику для загрузки данных с сервера
      // с учетом фильтров, сортировки и пагинации
      
      // Для простоты примера, делаем имитацию запроса
      setTimeout(() => {
        tableLoading.value = false;
      }, 500);
    };
    
    const handleSizeChange = (size) => {
      pageSize.value = size;
      reloadFilteredData();
    };
    
    const handleCurrentChange = (page) => {
      currentPage.value = page;
      reloadFilteredData();
    };
    
    // Модифицированная функция загрузки данных
    const loadDataPreview = async () => {
      if (!resultId.value) return;
      
      isPreviewLoading.value = true;
      previewError.value = null;
      
      try {
        // Загружаем данные с учетом пагинации
        const response = await preprocessingService.getDataPreview(
          resultId.value, 
          pageSize.value, 
          (currentPage.value - 1) * pageSize.value
        );
        
        previewData.value = response.data.preview;
        totalRecords.value = response.data.total_count || 0;
        
        // Инициализация видимости столбцов
        if (previewData.value && previewData.value.length > 0) {
          const columns = Object.keys(previewData.value[0]);
          columns.forEach(col => {
            if (visibleColumns[col] === undefined) {
              visibleColumns[col] = true;
            }
          });
        }
      } catch (error) {
        console.error('Ошибка загрузки предпросмотра:', error);
        previewError.value = 'Не удалось загрузить предпросмотр данных';
      } finally {
        isPreviewLoading.value = false;
      }
    };
    
    return {
      resultId,
      processingStatus,
      errorMessage,
      resultMetadata,
      isPreviewLoading,
      previewData,
      previewError,
      exportFormat,
      csvDelimiter,
      isExporting,
      appliedMethods,
      processingProgress,
      checkStatus,
      getProcessingStageTitle,
      loadDataPreview,
      exportData,
      isNewColumn,
      getMethodName,
      formatParameterName,
      formatParameterValue,
      goToPreprocessing,
      finishProcess,
      hasScalingParams,
      scalingMethodName,
      onMetadataUpdated,
      onInverseScalingApplied,
      scalingParams,
      visibleColumns,
      visibleColumnsList,
      defaultSortColumn,
      tableLoading,
      highlightedColumn,
      pageSize,
      currentPage,
      totalRecords,
      filterDialogVisible,
      currentFilterColumn,
      filterType,
      filterValue,
      filterRangeMin,
      filterRangeMax,
      handleColumnVisibility,
      handleSortChange,
      handleColumnDrag,
      getColumnFilters,
      filterColumn,
      openFilterDialog,
      applyAdvancedFilter,
      handleSizeChange,
      handleCurrentChange
    };
  },
});
</script>

<style scoped>
.preview-export-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.processing-card, .error-card, .data-preview, .export-card {
  margin-top: 20px;
  text-align: center;
}

.metadata-card {
  margin-bottom: 20px;
}

.processing-indicator, .error-message {
  padding: 40px;
}

.result-container {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.result-summary, .data-preview, .export-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.column-tag {
  margin: 5px;
}

.preview-loading, .no-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 50px;
}

.preview-error {
  padding: 20px;
}

.navigation-buttons {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
}

.export-options {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
}

.table-container {
  overflow-x: auto;
  margin-bottom: 20px;
  width: 100%;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.el-table {
  min-width: 800px; /* Обеспечивает минимальную ширину для горизонтальной прокрутки */
}

.el-table .cell {
  word-break: normal;
  white-space: nowrap;
}

.cell-content {
  display: inline-block;
  max-width: 300px;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.column-header i {
  cursor: pointer;
  color: #909399;
}

.column-header i:hover {
  color: #409EFF;
}

.highlight-column {
  background-color: #ecf5ff;
}

.pagination-controls {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.preview-content {
  width: 100%;
  overflow-x: auto;
}

.el-table {
  min-width: 800px; /* Обеспечивает горизонтальную прокрутку для узких экранов */
}

.el-table .cell {
  word-break: normal;
  white-space: nowrap;
}

.cell-content {
  display: inline-block;
  max-width: 300px;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.column-header i {
  cursor: pointer;
  color: #909399;
}

.column-header i:hover {
  color: #409EFF;
}

.highlight-column {
  background-color: #ecf5ff;
}

.pagination-controls {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>