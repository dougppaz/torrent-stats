package tasks

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/anacrolix/torrent"
)

type ScrapeClient interface {
	FailTask(taskID, errorMessage string) error
	UploadTorrent(infoHash, name string, totalSize int64, torrentFileBytes []byte, files []TorrentFilePayload) error
}

type TorrentFilePayload struct {
	Path   []string `json:"path"`
	Length int64    `json:"length"`
}

type ScrapeTorrentHandler struct {
	client ScrapeClient
}

func NewScrapeTorrentHandler(client ScrapeClient) *ScrapeTorrentHandler {
	return &ScrapeTorrentHandler{client: client}
}

func (h *ScrapeTorrentHandler) Execute(taskID, infoHash string) error {
	log.Printf("[INFO] Executing scrape_torrent for task_id=%s, info_hash=%s", taskID, infoHash)

	cfg := torrent.NewDefaultClientConfig()
	tmpDir, err := os.MkdirTemp("", "torrent-stats-worker-*")
	if err != nil {
		errMsg := fmt.Sprintf("failed to create temp dir: %v", err)
		log.Printf("[ERROR] %s", errMsg)
		_ = h.client.FailTask(taskID, errMsg)
		return fmt.Errorf("%s", errMsg)
	}
	defer os.RemoveAll(tmpDir)

	cfg.DataDir = tmpDir
	cfg.NoDefaultPortForwarding = true

	client, err := torrent.NewClient(cfg)
	if err != nil {
		errMsg := fmt.Sprintf("failed to create torrent client: %v", err)
		log.Printf("[ERROR] %s", errMsg)
		_ = h.client.FailTask(taskID, errMsg)
		return fmt.Errorf("%s", errMsg)
	}
	defer client.Close()

	magnetURI := fmt.Sprintf("magnet:?xt=urn:btih:%s", infoHash)
	t, err := client.AddMagnet(magnetURI)
	if err != nil {
		errMsg := fmt.Sprintf("failed to add magnet: %v", err)
		log.Printf("[ERROR] %s", errMsg)
		_ = h.client.FailTask(taskID, errMsg)
		return fmt.Errorf("%s", errMsg)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
	defer cancel()

	select {
	case <-t.GotInfo():
		// Metadata received successfully
	case <-ctx.Done():
		errMsg := fmt.Sprintf("timeout waiting for torrent metadata for info_hash=%s", infoHash)
		log.Printf("[ERROR] %s", errMsg)
		_ = h.client.FailTask(taskID, errMsg)
		return fmt.Errorf("%s", errMsg)
	}

	name := t.Name()
	totalSize := t.Length()

	var files []TorrentFilePayload
	for _, f := range t.Files() {
		fi := f.FileInfo()
		path := (&fi).BestPath()
		files = append(files, TorrentFilePayload{
			Path:   path,
			Length: f.Length(),
		})
	}

	metaInfo := t.Metainfo()
	var metaBuf bytes.Buffer
	if err := metaInfo.Write(&metaBuf); err != nil {
		errMsg := fmt.Sprintf("failed to encode metainfo: %v", err)
		log.Printf("[ERROR] %s", errMsg)
		_ = h.client.FailTask(taskID, errMsg)
		return fmt.Errorf("%s", errMsg)
	}

	if err := h.client.UploadTorrent(infoHash, name, totalSize, metaBuf.Bytes(), files); err != nil {
		errMsg := fmt.Sprintf("failed to upload torrent: %v", err)
		log.Printf("[ERROR] %s", errMsg)
		_ = h.client.FailTask(taskID, errMsg)
		return fmt.Errorf("%s", errMsg)
	}

	log.Printf("[INFO] Successfully scraped and uploaded torrent info_hash=%s (name=%s, size=%d)", infoHash, name, totalSize)
	return nil
}
