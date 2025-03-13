import { createStore } from 'vuex'

export default createStore({
  state: {
    datasetId: null,
    resultId: null,
    datasetInfo: null,
    scalingParams: null  // Параметры масштабирования данных
  },
  mutations: {
    setDatasetId(state, id) {
      state.datasetId = id;
    },
    setResultId(state, id) {
      state.resultId = id;
    },
    setDatasetInfo(state, info) {
      state.datasetInfo = info;
    },
    setScalingParams(state, params) {
      state.scalingParams = params;
    },
    clearPreprocessingState(state) {
      state.datasetId = null;
      state.resultId = null;
      state.datasetInfo = null;
      state.scalingParams = null;
    }
  },
  actions: {
    setDataset({ commit }, { id, info }) {
      commit('setDatasetId', id);
      if (info) {
        commit('setDatasetInfo', info);
      }
    },
    setResult({ commit }, id) {
      commit('setResultId', id);
    },
    setScalingParams({ commit }, params) {
      console.log('Сохранение параметров масштабирования в хранилище:', params);
      commit('setScalingParams', params);
    },
    resetState({ commit }) {
      commit('clearPreprocessingState');
    }
  },
  getters: {
    hasDataset: state => !!state.datasetId,
    hasResult: state => !!state.resultId,
    hasScalingParams: state => !!state.scalingParams
  }
})