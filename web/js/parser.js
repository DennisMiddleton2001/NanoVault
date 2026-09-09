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
 * Evaluates execution readiness based on active models vs total models.
 * - 0 / N: Red (Not ready)
 * - 1..(N-1) / N: Yellow (Partially ready)
 * - N / N: Green (Fully ready to run)
 */
export function evaluateWorkflowStatus(workflow) {
  const models = workflow.models || [];
  const total = models.length;

  if (total === 0) {
    return {
      label: '0/0 Ready',
      cls: 'bg-slate-900 text-slate-400 border-slate-700/60 hover:border-slate-500'
    };
  }

  // Count models present in active path (size > 0)
  const activeCount = models.filter(m => (m.active_size || 0) > 0).length;

  // 0 / N ready -> Red
  if (activeCount === 0) {
    return {
      label: `${activeCount}/${total} Ready`,
      cls: 'bg-rose-950 text-rose-300 border-rose-800/60 hover:border-rose-500'
    };
  }

  // N / N ready -> Green
  if (activeCount === total) {
    return {
      label: `${activeCount}/${total} Ready`,
      cls: 'bg-emerald-950 text-emerald-300 border-emerald-800/60 hover:border-emerald-500'
    };
  }

  // Partial (1 to N-1) -> Yellow/Amber
  return {
    label: `${activeCount}/${total} Ready`,
    cls: 'bg-amber-950 text-amber-300 border-amber-800/60 hover:border-amber-500'
  };
}

/**
 * Normalizes and categorizes pipeline execution responses.
 * Empty arrays are omitted.
 */
/**
 * Resolves source buckets into human-readable action summaries
 * based on the active pipeline opcode.
 */
export function parsePipelineResponse(res) {
  if (!res) {
    return {
      command: 'Unknown',
      statusText: 'FAILED',
      statusClass: 'border-rose-500/60',
      badgeClass: 'bg-rose-950 text-rose-400 border border-rose-800',
      ratio: '0/0',
      message: 'Empty response received from daemon',
      categories: []
    };
  }

  const isSuccess = res.successful === res.attempted && (!res.failed || res.failed.length === 0);
  const isPartial = res.successful > 0 && res.failed && res.failed.length > 0;
  const cmd = res.command || '';

  const isIngest = cmd.includes('Ingest') || cmd === '--i';
  const isTrim   = cmd.includes('Trim') || cmd === '--t';
  const isEvict  = cmd.includes('Evict') || cmd === '--e';

  let possibleCategories = [];

  if (isEvict) {
    // Evict exclusively tracks deletions and exclusions
    possibleCategories = [
      {
        key: 'failed',
        label: 'Faults',
        items: res.failed,
        borderClass: 'border-rose-500',
        textClass: 'text-rose-400'
      },
      {
        key: 'purged',
        label: 'Evicted from System',
        items: res.purged,
        borderClass: 'border-amber-500',
        textClass: 'text-amber-400'
      },
      {
        key: 'excluded',
        label: 'Excluded / Preserved',
        items: res.excluded,
        borderClass: 'border-slate-500',
        textClass: 'text-slate-400'
      }
    ];
  } else {
    // Context-aware labels for deployment, ingest, and trim
    let activeLabel = 'Already Active';
    let vaultLabel  = 'Restored from Vault';
    let purgedLabel = 'Purged from Cache';

    if (isIngest) {
      activeLabel = 'Vaulted from Active';
      vaultLabel  = 'Already in Vault';
    } else if (isTrim) {
      activeLabel = 'Active Preserved';
      vaultLabel  = 'Vault Retained';
      purgedLabel = 'Trimmed from Active';
    }

    possibleCategories = [
      {
        key: 'failed',
        label: 'Faults',
        items: res.failed,
        borderClass: 'border-rose-500',
        textClass: 'text-rose-400'
      },
      {
        key: 'active',
        label: activeLabel,
        items: res.active,
        borderClass: 'border-cyan-500',
        textClass: 'text-cyan-400'
      },
      {
        key: 'vault',
        label: vaultLabel,
        items: res.vault,
        borderClass: 'border-emerald-500',
        textClass: 'text-emerald-400'
      },
      {
        key: 'download',
        label: 'Downloaded to Active',
        items: res.download,
        borderClass: 'border-blue-500',
        textClass: 'text-blue-400'
      },
      {
        key: 'purged',
        label: purgedLabel,
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
  }

  // Filter out any empty lists
  const categories = possibleCategories.filter(
    cat => Array.isArray(cat.items) && cat.items.length > 0
  );

  return {
    command: cmd || 'Pipeline',
    statusText: isSuccess ? 'SUCCESS' : (isPartial ? 'PARTIAL' : 'FAILED'),
    statusClass: isSuccess 
      ? 'border-emerald-500/60' 
      : (isPartial ? 'border-amber-500/60' : 'border-rose-500/60'),
    badgeClass: isSuccess 
      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' 
      : (isPartial ? 'bg-amber-950 text-amber-400 border border-amber-800' : 'bg-rose-950 text-rose-400 border border-rose-800'),
    ratio: `${res.successful || 0}/${res.attempted || 0}`,
    message: res.message || '',
    categories
  };
}