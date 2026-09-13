/**
 * Low-level transport layer for dispatching CLI commands to the NanoVault daemon.
 */
export async function executeCommand(commandArray) {
  try {
    const response = await fetch('/api/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: commandArray })
    });

    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    return {
      status: 'FAILURE',
      message: error.message || 'Bridge link failed',
      retval: null
    };
  }
}

/**
 * Sweeps a workflow folder path via --list-workflows.
 */
export async function fetchWorkflows(workflowPath) {
  return await executeCommand(['--list-workflows', workflowPath]);
}

/**
 * Queries metal storage metrics via --query-metal-storage.
 */
export async function fetchMetalStorage() {
  return await executeCommand(['--query-metal-storage']);
}

/**
 * Dispatches a pipeline command flag against a workflow file path.
 */
export async function runPipeline(flag, fqPath) {
  return await executeCommand([flag, fqPath]);
}

async function loadComfyPath() {
    try {
        const response = await fetch('/api/config/workflow-path');
        const data = await response.json();
        
        if (data.status === "SUCCESS") {
            // Swap 'workflow-input' with the actual ID of your HTML element
            document.getElementById('workflow-input').value = data.workflow_path;
        }
    } catch (error) {
        console.error("Failed to load workflow path:", error);
    }
}