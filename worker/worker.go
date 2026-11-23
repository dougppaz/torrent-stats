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
	scrapeTimeout time.Duration
}

func NewWorker(client *Client, claimInterval, scrapeTimeout time.Duration) *Worker {
	return &Worker{
		client:        client,
		claimInterval: claimInterval,
		scrapeTimeout: scrapeTimeout,
	}
}

func (w *Worker) Start(ctx context.Context) {
	log.Printf("Worker started, polling claim interval: %v (instant claim when tasks available)", w.claimInterval)

	for {
		if ctx.Err() != nil {
			log.Println("Worker stopping...")
			return
		}

		claimed := w.pollAndExecute()
		if claimed {
			// Immediately poll next task without waiting
			continue
		}

		// No task available (204) or error, wait for claimInterval before next poll
		select {
		case <-ctx.Done():
			log.Println("Worker stopping...")
			return
		case <-time.After(w.claimInterval):
		}
	}
}

func (w *Worker) pollAndExecute() bool {
	task, claimed, err := w.client.ClaimTask()
	if err != nil {
		log.Printf("Error claiming task: %v", err)
		return false
	}

	if !claimed {
		return false
	}

	log.Printf("Claimed task %s (type: %s, hash: %s)", task.TaskID, task.TaskType, task.InfoHash)
	w.executeTaskStub(task)
	return true
}

func (w *Worker) executeTaskStub(task *Task) {
	scrapeTorrentHandler := tasks.NewScrapeTorrentHandler(w.client, w.scrapeTimeout)
	scrapeStatsHandler := tasks.NewScrapeStatsHandler(w.client)

	switch task.TaskType {
	case "scrape_torrent":
		_ = scrapeTorrentHandler.Execute(task.TaskID, task.InfoHash, task.Trackers)
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
