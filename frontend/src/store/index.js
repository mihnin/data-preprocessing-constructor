import { createStore } from 'vuex'

export default createStore({
  state: {
    datasetId: null,
    resultId: null,
    datasetInfo: null
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
    clearPreprocessingState(state) {
      state.datasetId = null;
      state.resultId = null;
      state.datasetInfo = null;
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
    resetState({ commit }) {
      commit('clearPreprocessingState');
    }
  },
  getters: {
    hasDataset: state => !!state.datasetId,
    hasResult: state => !!state.resultId
  }
})