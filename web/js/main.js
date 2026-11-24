import { fetchWorkflows, fetchMetalStorage, runPipelineStream, auditModel } from './api.js';
import { formatBytes, evaluateWorkflowStatus, parsePipelineResponse, parseModelAuditResponse } from './parser.js';
import { NanoVaultQueue } from './queue.js';
import { buildModelInspectorData } from './ui.js';

const { createApp, ref, onMounted, nextTick } = Vue;

const MAX_STREAM_LINES = 1000;

const FLAG_LABELS = {
  '--a': 'DeploymentPipeline',
  '--as': 'SpotDeploy',
  '--i': 'IngestPipeline',
  '--t': 'TrimPipeline',
  '--e': 'EvictPipeline'
};

createApp({
  setup() {
    const workflowPath = ref('');

    function updateWorkflowPath(newPath) {
      workflowPath.value = newPath;
      localStorage.setItem('sanctuary_workflow_path', newPath);
    }

    fetch('/api/config/workflow-path', { cache: 'no-store' })
      .then(res => res.json())
      .then(data => {
        if (data.status === "SUCCESS") {
          updateWorkflowPath(data.workflow_path);
          loadWorkflows();
        }
      })
      .catch(err => console.error('Fetch failed:', err));

    // Core dashboard state
    const workflows = ref([]);
    const activeSize = ref('0 B');
    const vaultSize = ref('0 B');
    const lastResult = ref('System initialized under the Oak Tree Shade.');
    const executionLogs = ref([]);
    const toasts = ref([]);
    const isRefreshing = ref(false);

    // Reverse model lookup (audit) state
    const auditedModel = ref(null);
    const highlightedWorkflows = ref([]);
    const isAuditing = ref(false);

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

    // Smart auto-scroll for an individual card's live console box
    const scrollConsoleIfPinned = async (taskId) => {
      const el = document.querySelector(`[data-console-id="${taskId}"]`);
      const wasNearBottom = !el || (el.scrollHeight - el.scrollTop - el.clientHeight < 48);
      await nextTick();
      if (wasNearBottom) {
        const updatedEl = document.querySelector(`[data-console-id="${taskId}"]`);
        if (updatedEl) {
          updatedEl.scrollTop = updatedEl.scrollHeight;
        }
      }
    };

    const WGET_DOT_REGEX = /^\s*\d+K\s+[.\s]+/;

    // Appends raw stdout/stderr text while collapsing \r bars AND wget dot-progress lines
    const appendStreamChunk = (entry, chunk) => {
      if (!chunk) return;
      const normalized = chunk.replace(/\r\n/g, '\n');
      if (entry.rawLogs.length === 0) {
        entry.rawLogs.push('');
      }

      const tokens = normalized.split(/(\r|\n)/);
      for (const token of tokens) {
        if (!token) continue;
        if (token === '\n') {
          const lastIdx = entry.rawLogs.length - 1;
          // If both the just-completed line and the one above it are wget dot lines, overwrite in place
          if (
            lastIdx >= 1 &&
            WGET_DOT_REGEX.test(entry.rawLogs[lastIdx]) &&
            WGET_DOT_REGEX.test(entry.rawLogs[lastIdx - 1])
          ) {
            entry.rawLogs[lastIdx - 1] = entry.rawLogs[lastIdx];
            entry.rawLogs[lastIdx] = '';
          } else {
            entry.rawLogs.push('');
          }

          entry._crPending = false;
          if (entry.rawLogs.length > MAX_STREAM_LINES) {
            entry.rawLogs.splice(0, entry.rawLogs.length - MAX_STREAM_LINES);
          }
        } else if (token === '\r') {
          entry._crPending = true;
        } else {
          const lastIdx = entry.rawLogs.length - 1;
          if (entry._crPending) {
            entry.rawLogs[lastIdx] = token;
            entry._crPending = false;
          } else {
            entry.rawLogs[lastIdx] += token;
          }
        }
      }
    };
    // Light syntax tinting for streamed console lines
    const getConsoleLineClass = (line) => {
      if (!line) return 'text-slate-400';
      if (/error|failed|exception|traceback|fatal/i.test(line)) return 'text-rose-400';
      if (/warn|warning|retrying/i.test(line)) return 'text-amber-300';
      if (/100%|saved|success|complete|done/i.test(line)) return 'text-emerald-400';
      return 'text-slate-300';
    };

    // Initialize the serial queue engine with live stdout streaming
    const queueEngine = new NanoVaultQueue(
      async (flag, filePath, onChunk) => {
        return await runPipelineStream(flag, filePath, onChunk);
      },
      ({ activeTask: current, pendingCount: pending, completedTask }) => {
        activeTask.value = current;
        pendingCount.value = pending;

        // 1. When a task starts, create its live In-Flight card at the top
        if (current && !executionLogs.value.some(e => e.taskId === current.id)) {
          executionLogs.value.unshift({
            taskId: current.id,
            isRunning: true,
            command: FLAG_LABELS[current.flag] || current.flag,
            target: current.workflowName,
            statusText: 'RUNNING',
            statusClass: 'border-amber-500/60 shadow-[0_0_16px_rgba(245,158,11,0.12)]',
            badgeClass: 'bg-amber-950 text-amber-300 border border-amber-700 animate-pulse',
            message: `Executing ${current.flag} on ${current.workflowName}...`,
            ratio: '...',
            categories: [],
            rawLogs: [],
            showRawLog: true,
            _crPending: false,
            timestamp: new Date().toLocaleTimeString()
          });
          scrollToTop();
        }

        // 2. When a task completes, transform its In-Flight card in place
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

          const existingCard = executionLogs.value.find(e => e.taskId === completedTask.id);
          if (existingCard) {
            // Drop trailing empty placeholder line if present
            if (existingCard.rawLogs.length > 0 && existingCard.rawLogs[existingCard.rawLogs.length - 1] === '') {
              existingCard.rawLogs.pop();
            }

            existingCard.isRunning = false;
            existingCard.command = parsed.command;
            existingCard.target = completedTask.workflowName;
            existingCard.statusText = parsed.statusText;
            existingCard.statusClass = parsed.statusClass;
            existingCard.badgeClass = parsed.badgeClass;
            existingCard.message = parsed.message;
            existingCard.ratio = parsed.ratio;
            existingCard.categories = parsed.categories;
            existingCard.timestamp = new Date().toLocaleTimeString();
            // Auto-collapse raw stdout on clean success; keep open on failure/partial
            existingCard.showRawLog = parsed.statusText !== 'SUCCESS';
          } else {
            executionLogs.value.unshift({
              taskId: completedTask.id,
              isRunning: false,
              command: parsed.command,
              target: completedTask.workflowName,
              statusText: parsed.statusText,
              statusClass: parsed.statusClass,
              badgeClass: parsed.badgeClass,
              message: parsed.message,
              ratio: parsed.ratio,
              categories: parsed.categories,
              rawLogs: [],
              showRawLog: false,
              timestamp: new Date().toLocaleTimeString()
            });
          }

          loadWorkflows();
          scrollToTop();
        }
      },
      // 3. Stream chunk handler -> feeds the matching In-Flight card live
      (taskId, chunk) => {
        const entry = executionLogs.value.find(e => e.taskId === taskId);
        if (!entry) return;
        appendStreamChunk(entry, chunk);
        scrollConsoleIfPinned(taskId);
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

    // Modal state for model inspector
    const inspectorModal = ref({
      isOpen: false,
      title: '',
      content: '',
      items: []
    });

    const inspectWorkflow = (wf) => {
      const details = buildModelInspectorData(wf);

      const summary = details.map(d => {
        const hasActive = d.state.includes('A');
        const hasVault  = d.state.includes('V');

        const flagA = hasActive ? 'A' : '.';
        const flagV = hasVault  ? 'V' : '.';
        const tag = `[${flagA}${flagV}]`;

        const folderPath = d.folder ? `models/${d.folder}/` : 'models/';
        return `${tag} ${folderPath}${d.name}`;
      }).join('\n');

      inspectorModal.value = {
        isOpen: true,
        title: `Model Dependencies: ${wf.name}`,
        content: summary,
        items: details
      };
    };

    const copyInspectorContent = async () => {
      try {
        await navigator.clipboard.writeText(inspectorModal.value.content);
        addToast("Copied", "Model list copied to clipboard.");
      } catch (err) {
        addToast("Error", "Failed to copy to clipboard.");
      }
    };

    const copyLogEntry = async (entry) => {
      const lines = [
        `[${entry.statusText}] ${entry.command} — ${entry.target} (${entry.timestamp})`
      ];

      if (entry.message) {
        lines.push(entry.message);
      }

      if (Array.isArray(entry.categories) && entry.categories.length > 0) {
        entry.categories.forEach(cat => {
          lines.push('');
          lines.push(`${cat.label.toUpperCase()} (${cat.items.length}):`);
          cat.items.forEach(item => lines.push(`• ${item}`));
        });
      }

      try {
        await navigator.clipboard.writeText(lines.join('\n'));
        addToast("Copied", `${entry.command} result copied to clipboard.`);
      } catch (err) {
        addToast("Error", "Failed to copy result to clipboard.");
      }
    };

    const closeInspectorModal = () => {
      inspectorModal.value.isOpen = false;
    };

    // Reverse model lookup helpers
    const isWorkflowHighlighted = (wfName) => {
      return highlightedWorkflows.value.includes(wfName);
    };

    const clearModelAudit = () => {
      auditedModel.value = null;
      highlightedWorkflows.value = [];
    };

    const runModelAudit = async (modelName) => {
      if (!modelName || typeof modelName !== 'string' || isAuditing.value) return;

      const cleanName = modelName.trim();
      if (!cleanName) return;

      isAuditing.value = true;
      try {
        const raw = await auditModel(cleanName, workflowPath.value);

        if (raw.status === 'SUCCESS' && raw.retval) {
          const parsed = parseModelAuditResponse(raw.retval);

          auditedModel.value = parsed.modelName;
          highlightedWorkflows.value = parsed.dependentWorkflowNames;
          lastResult.value = `retval: ${JSON.stringify(raw.retval)}`;

          executionLogs.value.unshift({
            taskId: `audit_${Date.now()}`,
            isRunning: false,
            command: parsed.command,
            target: parsed.modelName,
            statusText: parsed.statusText,
            statusClass: parsed.statusClass,
            badgeClass: parsed.badgeClass,
            message: parsed.message,
            ratio: parsed.ratio,
            categories: parsed.categories,
            rawLogs: [],
            showRawLog: false,
            timestamp: new Date().toLocaleTimeString()
          });

          if (inspectorModal.value.isOpen) {
            inspectorModal.value.isOpen = false;
          }

          addToast("Model Audit Complete", `${parsed.modelName}: ${parsed.refCount} workflow(s) found.`);
          scrollToTop();
        } else {
          const errMsg = raw.message || 'Audit command failed';
          lastResult.value = `ERROR: ${errMsg}`;
          addToast("Audit Error", errMsg, 5000);
        }
      } catch (err) {
        lastResult.value = `ERROR: ${err.message}`;
        addToast("Audit Error", err.message || "Failed to audit model.", 5000);
      } finally {
        isAuditing.value = false;
      }
    };

    const loadWorkflows = async () => {
      const targetPath = workflowPath.value?.trim();
      if (!targetPath) return false;

      try {
        const data = await fetchWorkflows(targetPath);
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

    onMounted(async () => {
      try {
        const res = await fetch('/api/config/workflow-path', { cache: 'no-store' });
        const data = await res.json();
        if (data.status === 'SUCCESS' && data.workflow_path) {
          updateWorkflowPath(data.workflow_path);
          await loadWorkflows();
        }
      } catch (err) {
        console.error('Failed to load workflow path:', err);
      }
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
      inspectorModal,
      copyInspectorContent,
      copyLogEntry,
      closeInspectorModal,
      inspectWorkflow,
      queryMetalStorage,
      auditedModel,
      highlightedWorkflows,
      isAuditing,
      runModelAudit,
      clearModelAudit,
      isWorkflowHighlighted,
      getConsoleLineClass
    };
  }
}).mount('#app');