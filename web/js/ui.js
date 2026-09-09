/**
 * Resolves abbreviated state codes:
 * - 'VA' : In Vault & Active
 * - 'A'  : Active only
 * - 'V'  : Vault only
 * - 'M'  : Missing
 */
export function buildModelInspectorData(workflow) {
  const models = workflow.models || [];

  return models.map(m => {
    // Detect active presence
    const hasActive = 
      (Number(m.active_size) > 0) || 
      m.in_active === true || 
      m.active === true ||
      m.status === 'active' ||
      m.location === 'active';

    // Detect vault presence
    const hasVault = 
      (Number(m.vault_size) > 0) || 
      m.in_vault === true || 
      m.vault === true ||
      m.status === 'vault' ||
      m.location === 'vault';

    let code = 'M';
    let color = 'text-rose-400';

    if (hasActive && hasVault) {
      code = 'VA';
      color = 'text-cyan-400';
    } else if (hasActive) {
      code = 'A';
      color = 'text-emerald-400';
    } else if (hasVault) {
      code = 'V';
      color = 'text-amber-400';
    }

    const resolvedFolder = 
      m.model_path || 
      m.folder || 
      m.target_folder || 
      m.type || 
      'root';

    const resolvedName = 
      m.model_name || 
      m.name || 
      m.filename || 
      'Unknown Model';

    return {
      name: resolvedName,
      folder: resolvedFolder,
      code: code,
      state: code, // Backward compatibility for templates using d.state
      color: color
    };
  });
}