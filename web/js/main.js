import { fetchWorkflows, fetchMetalStorage, runPipeline } from './api.js';
import { formatBytes, evaluateWorkflowStatus, parsePipelineResponse } from './parser.js';
import { NanoVaultQueue } from './queue.js';
import { buildModelInspectorData } from './ui.js';

const { createApp, ref, onMounted, nextTick } = Vue;

createApp({
  setup() {
    const savedPath = localStorage.getItem('sanctuary_workflow_path');
    const workflowPath = ref(savedPath || '/home/darth-tedious/.sovereign-ai/ComfyUI/user/default/workflows/');
    localStorage.setItem('sanctuary_workflow_path', workflowPath.value);

    const workflows = ref([]);
    const activeSize = ref('0 B');
    const vaultSize = ref('0 B');
    const lastResult = ref('System initialized under the Oak Tree Shade.');
    const executionLogs = ref([]);
    const toasts = ref([]);
    const isRefreshing = ref(false);

    // Queue state
    const activeTask = ref(null);
    const pendingCount = ref(0);

    // Resizable split pane state
    const leftWidth = ref(520);
    const isResizing = ref(false);

    const startResize = (e) => {
      isResizing.value = true;
      document.addEventListener('mousemove', onResize);
      document.addEventListener('mouseup', stopResize);
      e.preventDefault();
    };

    const onResize = (e) => {
      if (!isResizing.value) return;
      const newWidth = e.clientX;
      if (newWidth > 320 && newWidth < window.innerWidth - 400) {
        leftWidth.value = newWidth;
      }
    };

    const stopResize = () => {
      isResizing.value = false;
      document.removeEventListener('mousemove', onResize);
      document.removeEventListener('mouseup', stopResize);
    };

    const addToast = (title, message, duration = 4000) => {
      const id = Date.now();
      toasts.value.push({ id, title, message });
      setTimeout(() => {
        toasts.value = toasts.value.filter(t => t.id !== id);
      }, duration);
    };

    const scrollToTop = async () => {
      await nextTick();
      const container = document.querySelector('.overflow-y-auto.font-mono');
      if (container) {
        container.scrollTo({ top: 0, behavior: 'smooth' });
      }
    };

    const scrollToBottom = async () => {
      await nextTick();
      const container = document.querySelector('.overflow-y-auto.font-mono');
      if (container) container.scrollTop = container.scrollHeight;
    };

    // Initialize the serial queue engine
    const queueEngine = new NanoVaultQueue(
      async (flag, filePath) => {
        return await runPipeline(flag, filePath);
      },
      ({ activeTask: current, pendingCount: pending, completedTask }) => {
        activeTask.value = current;
        pendingCount.value = pending;

        if (completedTask) {
          const raw = completedTask.rawResult;
          let parsed;

          if (raw.status === 'SUCCESS' && raw.retval) {
            parsed = parsePipelineResponse(raw.retval);
            lastResult.value = `retval: ${JSON.stringify(raw.retval)}`;
          } else {
            parsed = parsePipelineResponse({
              command: completedTask.flag,
              attempted: 1,
              successful: 0,
              failed: [raw.message || 'Execution error'],
              message: raw.message || 'Pipeline failed'
            });
            lastResult.value = `ERROR: ${raw.message}`;
          }

          executionLogs.value.unshift({
            command: parsed.command,
            target: completedTask.workflowName,
            statusText: parsed.statusText,
            statusClass: parsed.statusClass,
            badgeClass: parsed.badgeClass,
            message: parsed.message,
            ratio: parsed.ratio,
            categories: parsed.categories,
            timestamp: new Date().toLocaleTimeString()
          });

          // Refresh storage & workflows on completion
          loadWorkflows();
          scrollToTop();
        }
      }
    );

    const queryMetalStorage = async () => {
      isRefreshing.value = true;
      try {
        const data = await fetchMetalStorage();
        if (data.status === 'SUCCESS' && data.retval) {
          activeSize.value = formatBytes(data.retval.active_usage);
          vaultSize.value = formatBytes(data.retval.vault_usage);
          addToast("Storage Synchronized", "Metal storage metrics updated.");
        }
      } catch (err) {
        addToast("Query Error", "Failed to communicate with backend.", 5000);
      } finally {
        isRefreshing.value = false;
      }
    };

    const loadWorkflows = async () => {
      localStorage.setItem('sanctuary_workflow_path', workflowPath.value);
      try {
        const data = await fetchWorkflows(workflowPath.value);
        if (data.status === 'SUCCESS') {
          const rawList = Array.isArray(data.retval) ? data.retval : [];

          workflows.value = rawList.map(wf => {
            const active = wf.active_size || 0;
            const vault = wf.vault_size || 0;
            const combined = active + vault;

            return {
              name: wf.name,
              fq_path: wf.fq_path,
              rawActiveSize: active,
              rawVaultSize: vault,
              displaySize: combined > 0 ? `Active: ${formatBytes(active)} | Vault: ${formatBytes(vault)}` : '0 B',
              models: wf.models || [],
              statusBadge: evaluateWorkflowStatus(wf)
            };
          });

          await queryMetalStorage();
          return true;
        }
      } catch (error) {
        addToast("Connection Error", error.message, 5000);
        return false;
      }
    };

    const enqueueCommand = (flag, wf) => {
      if (flag === '--e') {
        const confirmed = window.confirm(`WARNING: Evict "${wf.name}"? This removes models from active paths and vault.`);
        if (!confirmed) {
          addToast("Aborted", "Eviction cancelled.");
          return;
        }
      }
      queueEngine.enqueue(flag, wf);
      addToast("Enqueued", `${flag} for ${wf.name}`);
    };

    const inspectWorkflow = (wf) => {
      const details = buildModelInspectorData(wf);
      const summary = details.map(d => `[${d.state}] ${d.name}(${d.folder})`).join('\n');
      alert(`Model Dependencies for ${wf.name}:\n\n${summary}`);
    };

    onMounted(() => {
      loadWorkflows();
    });

    return {
      workflowPath,
      workflows,
      activeSize,
      vaultSize,
      lastResult,
      executionLogs,
      toasts,
      isRefreshing,
      activeTask,
      pendingCount,
      leftWidth,
      startResize,
      loadWorkflows,
      enqueueCommand,
      inspectWorkflow,
      queryMetalStorage
    };
  }
}).mount('#app');