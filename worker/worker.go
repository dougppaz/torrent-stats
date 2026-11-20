package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/betorbr/torrent-stats-worker/tasks"
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
	scrapeTorrentHandler := tasks.NewScrapeTorrentHandler(w.client)
	scrapeStatsHandler := tasks.NewScrapeStatsHandler(w.client)

	switch task.TaskType {
	case "scrape_torrent":
		_ = scrapeTorrentHandler.Execute(task.TaskID, task.InfoHash)
	case "scrape_stats":
		trackerURL := ""
		if task.TrackerURL != nil {
			trackerURL = *task.TrackerURL
		}
		_ = scrapeStatsHandler.ExecuteWithTracker(task.TaskID, task.InfoHash, trackerURL)
	default:
		errMsg := fmt.Sprintf("unknown task type: %s", task.TaskType)
		log.Printf("[ERROR] %s for task_id=%s", errMsg, task.TaskID)
		_ = w.client.FailTask(task.TaskID, errMsg)
	}
}
