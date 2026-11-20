package tasks

import (
	"log"
)

type ScrapeStatsHandler struct {
	client FailClient
}

func NewScrapeStatsHandler(client FailClient) *ScrapeStatsHandler {
	return &ScrapeStatsHandler{client: client}
}

func (h *ScrapeStatsHandler) Execute(taskID, infoHash string) error {
	errMsg := "scrape_stats task execution not yet implemented"
	log.Printf("[ERROR] %s (task_id=%s, info_hash=%s)", errMsg, taskID, infoHash)
	if err := h.client.FailTask(taskID, errMsg); err != nil {
		log.Printf("Failed to report task failure to API: %v", err)
	}
	return nil
}
