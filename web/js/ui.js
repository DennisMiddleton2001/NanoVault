/**
 * Builds formatted text or modal contents for model inspect checks.
 */
export function buildModelInspectorData(workflow) {
  const models = workflow.models || [];
  return models.map(m => {
    let state = 'Missing';
    let color = 'text-rose-400';

    if (m.active_size > 0) {
      state = 'Active';
      color = 'text-emerald-400';
    } else if (m.vault_size > 0) {
      state = 'Vaulted';
      color = 'text-amber-400';
    }

    return {
      name: m.model_name,
      folder: m.model_path,
      url: m.model_url,
      state,
      color
    };
  });
}