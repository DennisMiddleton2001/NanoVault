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
 * Dispatches a non-streaming pipeline command flag against a workflow file path.
 */
export async function runPipeline(flag, fqPath) {
  return await executeCommand([flag, fqPath]);
}

/**
 * Dispatches a pipeline command via /api/execute-stream, invoking onChunk(text)
 * for every live stdout/stderr packet and resolving with the final result object.
 */
export async function runPipelineStream(flag, fqPath, onChunk) {
  try {
    const response = await fetch('/api/execute-stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: [flag, fqPath] })
    });

    if (!response.ok) {
      throw new Error(`HTTP Error: ${response.status} ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error('ReadableStream not supported by browser.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let finalResult = null;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Hold trailing incomplete line

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        try {
          const msg = JSON.parse(trimmed);
          if (msg.type === 'stdout' && typeof onChunk === 'function') {
            onChunk(msg.data);
          } else if (msg.type === 'result') {
            finalResult = msg;
          }
        } catch (parseErr) {
          console.warn('Skipped malformed stream frame:', trimmed);
        }
      }
    }

    // Flush any remaining buffered line
    if (buffer.trim()) {
      try {
        const msg = JSON.parse(buffer.trim());
        if (msg.type === 'stdout' && typeof onChunk === 'function') {
          onChunk(msg.data);
        } else if (msg.type === 'result') {
          finalResult = msg;
        }
      } catch (e) {
        // ignore trailing partial frame
      }
    }

    return finalResult || {
      status: 'FAILURE',
      message: 'Stream closed without final result packet.',
      retval: null
    };
  } catch (error) {
    return {
      status: 'FAILURE',
      message: error.message || 'Streaming bridge link failed',
      retval: null
    };
  }
}

/**
 * Runs reverse model lookup via --audit-model.
 * Sends ["--audit-model", modelName] or ["--audit-model", modelName, workflowPath].
 */
export async function auditModel(modelName, workflowPath = '') {
  const args = ['--audit-model', modelName];
  if (workflowPath && workflowPath.trim()) {
    args.push(workflowPath.trim());
  }
  return await executeCommand(args);
}