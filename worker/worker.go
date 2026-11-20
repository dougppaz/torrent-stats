package main

import (
	"context"
	"log"
	"time"
)

type Worker struct {
	client        *Client
	claimInterval time.Duration
}

func NewWorker(client *Client, claimInterval time.Duration) *Worker {
	return &Worker{
		client:        client,
		claimInterval: claimInterval,
	}
}

func (w *Worker) Start(ctx context.Context) {
	log.Printf("Worker started, polling claim endpoint every %v", w.claimInterval)
	ticker := time.NewTicker(w.claimInterval)
	defer ticker.Stop()

	w.pollAndExecute()

	for {
		select {
		case <-ctx.Done():
			log.Println("Worker stopping...")
			return
		case <-ticker.C:
			w.pollAndExecute()
		}
	}
}

func (w *Worker) pollAndExecute() {
	task, claimed, err := w.client.ClaimTask()
	if err != nil {
		log.Printf("Error claiming task: %v", err)
		return
	}

	if !claimed {
		return
	}

	log.Printf("Claimed task %s (type: %s, hash: %s)", task.TaskID, task.TaskType, task.InfoHash)
	w.executeTaskStub(task)
}

func (w *Worker) executeTaskStub(task *Task) {
	log.Printf("[ERROR] Task execution not yet implemented for task_type=%s, task_id=%s, info_hash=%s", task.TaskType, task.TaskID, task.InfoHash)
}
