
// State Management
export const state = {
    wavesurfer: null,
    currentTask: null,
    showingAllHistory: false,
    terminalInterval: null,
    terminalPaused: false,
    terminalWs: null,
    terminalRetryCount: 0,
    reportsChart: null
};

// Toggle state helpers
export function toggleHistoryFilter(val) {
    state.showingAllHistory = val;
}
