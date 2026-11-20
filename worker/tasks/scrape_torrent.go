package tasks

import (
	"log"
)

type ScrapeTorrentHandler struct {
	client FailClient
}

func NewScrapeTorrentHandler(client FailClient) *ScrapeTorrentHandler {
	return &ScrapeTorrentHandler{client: client}
}

func (h *ScrapeTorrentHandler) Execute(taskID, infoHash string) error {
	errMsg := "scrape_torrent task execution not yet implemented"
	log.Printf("[ERROR] %s (task_id=%s, info_hash=%s)", errMsg, taskID, infoHash)
	if err := h.client.FailTask(taskID, errMsg); err != nil {
		log.Printf("Failed to report task failure to API: %v", err)
	}
	return nil
}
