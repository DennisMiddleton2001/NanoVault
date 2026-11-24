/**
 * Single-worker serial queue state machine with live stream forwarding.
 */
export class NanoVaultQueue {
  constructor(executorFn, onStateChange, onStreamChunk = null) {
    this.queue = [];
    this.activeTask = null;
    this.executorFn = executorFn;
    this.onStateChange = onStateChange;
    this.onStreamChunk = onStreamChunk;
  }

  enqueue(flag, workflow) {
    const task = {
      id: `task_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      flag,
      workflowName: workflow.name,
      filePath: workflow.fq_path,
      enqueuedAt: new Date()
    };
    this.queue.push(task);
    this.notify();
    this.processNext();
    return task.id;
  }

  async processNext() {
    if (this.activeTask || this.queue.length === 0) return;

    this.activeTask = this.queue.shift();
    this.activeTask.startedAt = new Date();
    this.notify();

    const currentTaskId = this.activeTask.id;

    try {
      const response = await this.executorFn(
        this.activeTask.flag,
        this.activeTask.filePath,
        (chunk) => {
          if (this.onStreamChunk) {
            this.onStreamChunk(currentTaskId, chunk);
          }
        }
      );
      this.activeTask.rawResult = response;
    } catch (err) {
      this.activeTask.rawResult = {
        status: 'FAILURE',
        message: err.message || 'Worker thread failed',
        retval: null
      };
    } finally {
      const completed = this.activeTask;
      this.activeTask = null;
      this.notify(completed);
      this.processNext();
    }
  }

  notify(completedTask = null) {
    if (this.onStateChange) {
      this.onStateChange({
        activeTask: this.activeTask,
        pendingCount: this.queue.length,
        queue: [...this.queue],
        completedTask
      });
    }
  }
}