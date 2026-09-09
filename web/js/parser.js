/**
 * Format bytes into human-readable strings.
 */
export function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Evaluates the model status for a workflow.
 */
export function evaluateWorkflowStatus(workflow) {
  const models = workflow.models || [];
  let active = 0;
  let vaulted = 0;
  let missing = 0;

  models.forEach(m => {
    if (m.active_size > 0) active++;
    else if (m.vault_size > 0) vaulted++;
    else missing++;
  });

  if (missing > 0) {
    return {
      label: `${missing} Missing`,
      cls: 'bg-rose-950 text-rose-300 border-rose-800/60 hover:border-rose-500'
    };
  }
  if (vaulted > 0) {
    return {
      label: `${vaulted} Vaulted`,
      cls: 'bg-amber-950 text-amber-300 border-amber-800/60 hover:border-amber-500'
    };
  }
  return {
    label: `${active}/${active} Ready`,
    cls: 'bg-emerald-950 text-emerald-300 border-emerald-800/60 hover:border-emerald-500'
  };
}

/**
 * Normalizes and categorizes pipeline execution responses.
 * Empty arrays are omitted.
 */
export function parsePipelineResponse(res) {
  if (!res) {
    return {
      command: 'Unknown',
      statusText: 'Failed',
      statusClass: 'border-rose-500/60',
      badgeClass: 'bg-rose-950 text-rose-400 border border-rose-800',
      ratio: '0/0',
      message: 'Empty response received from daemon',
      categories: []
    };
  }

  const isSuccess = res.successful === res.attempted && (!res.failed || res.failed.length === 0);
  const isPartial = res.successful > 0 && res.failed && res.failed.length > 0;

  const possibleCategories = [
    {
      key: 'failed',
      label: 'Faults',
      items: res.failed,
      borderClass: 'border-rose-500',
      textClass: 'text-rose-400'
    },
    {
      key: 'active',
      label: 'Already Active',
      items: res.active,
      borderClass: 'border-cyan-500',
      textClass: 'text-cyan-400'
    },
    {
      key: 'vault',
      label: 'Restored from Vault',
      items: res.vault,
      borderClass: 'border-emerald-500',
      textClass: 'text-emerald-400'
    },
    {
      key: 'download',
      label: 'Downloaded',
      items: res.download,
      borderClass: 'border-blue-500',
      textClass: 'text-blue-400'
    },
    {
      key: 'purged',
      label: 'Purged from Cache',
      items: res.purged,
      borderClass: 'border-amber-500',
      textClass: 'text-amber-400'
    },
    {
      key: 'excluded',
      label: 'Excluded Assets',
      items: res.excluded,
      borderClass: 'border-slate-500',
      textClass: 'text-slate-400'
    }
  ];

  // Only retain populated arrays
  const categories = possibleCategories.filter(cat => Array.isArray(cat.items) && cat.items.length > 0);

  return {
    command: res.command || 'Pipeline',
    statusText: isSuccess ? 'SUCCESS' : (isPartial ? 'PARTIAL' : 'FAILED'),
    statusClass: isSuccess ? 'border-emerald-500/60' : (isPartial ? 'border-amber-500/60' : 'border-rose-500/60'),
    badgeClass: isSuccess 
      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' 
      : (isPartial ? 'bg-amber-950 text-amber-400 border border-amber-800' : 'bg-rose-950 text-rose-400 border border-rose-800'),
    ratio: `${res.successful || 0}/${res.attempted || 0}`,
    message: res.message || '',
    categories
  };
}