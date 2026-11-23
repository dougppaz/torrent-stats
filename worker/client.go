package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"mime/multipart"
	"net/http"
	"strconv"
	"time"

	"github.com/betorbr/torrent-stats-worker/tasks"
)

type Task struct {
	TaskID         string   `json:"task_id"`
	InfoHash       string   `json:"info_hash"`
	TaskType       string   `json:"task_type"`
	TrackerURL     *string  `json:"tracker_url"`
	UpdatedAt      *string  `json:"updated_at"`
	LeaseExpiresAt string   `json:"lease_expires_at"`
	Trackers       []string `json:"trackers"`
}

type TaskFailureRequest struct {
	ErrorMessage string `json:"error_message"`
}

type TrackerStatsSubmit struct {
	TrackerURL string `json:"tracker_url"`
	Success    bool   `json:"success"`
	Seeds      int    `json:"seeds"`
	Peers      int    `json:"peers"`
}

type Client struct {
	APIURL     string
	WorkerKey  string
	HTTPClient *http.Client
}

func NewClient(apiURL, workerKey string) *Client {
	return &Client{
		APIURL:     apiURL,
		WorkerKey:  workerKey,
		HTTPClient: &http.Client{Timeout: 10 * time.Second},
	}
}

func (c *Client) ClaimTask() (*Task, bool, error) {
	reqURL := fmt.Sprintf("%s/worker/tasks/claim", c.APIURL)
	req, err := http.NewRequest(http.MethodPost, reqURL, nil)
	if err != nil {
		return nil, false, err
	}
	req.Header.Set("X-Worker-Key", c.WorkerKey)

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, false, err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNoContent {
		return nil, false, nil
	}

	if resp.StatusCode != http.StatusOK {
		return nil, false, fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	var task Task
	if err := json.NewDecoder(resp.Body).Decode(&task); err != nil {
		return nil, false, err
	}

	return &task, true, nil
}

func (c *Client) FailTask(taskID, errorMessage string) error {
	reqURL := fmt.Sprintf("%s/worker/tasks/%s/fail", c.APIURL, taskID)
	body := TaskFailureRequest{ErrorMessage: errorMessage}
	var buf bytes.Buffer
	if err := json.NewEncoder(&buf).Encode(body); err != nil {
		return err
	}

	req, err := http.NewRequest(http.MethodPost, reqURL, &buf)
	if err != nil {
		return err
	}
	req.Header.Set("X-Worker-Key", c.WorkerKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status code for fail report: %d", resp.StatusCode)
	}
	return nil
}

func (c *Client) SubmitStats(infoHash, trackerURL string, success bool, seeds, peers int) error {
	reqURL := fmt.Sprintf("%s/worker/torrents/%s/stats", c.APIURL, infoHash)
	body := TrackerStatsSubmit{
		TrackerURL: trackerURL,
		Success:    success,
		Seeds:      seeds,
		Peers:      peers,
	}
	var buf bytes.Buffer
	if err := json.NewEncoder(&buf).Encode(body); err != nil {
		return err
	}

	req, err := http.NewRequest(http.MethodPost, reqURL, &buf)
	if err != nil {
		return err
	}
	req.Header.Set("X-Worker-Key", c.WorkerKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status code for stats submission: %d", resp.StatusCode)
	}
	return nil
}

func (c *Client) UploadTorrent(infoHash, name string, totalSize int64, torrentFileBytes []byte, files []tasks.TorrentFilePayload) error {
	reqURL := fmt.Sprintf("%s/worker/torrents", c.APIURL)

	bodyBuf := &bytes.Buffer{}
	writer := multipart.NewWriter(bodyBuf)

	_ = writer.WriteField("info_hash", infoHash)
	_ = writer.WriteField("name", name)
	_ = writer.WriteField("total_size", strconv.FormatInt(totalSize, 10))

	if len(files) > 0 {
		filesJSON, err := json.Marshal(files)
		if err == nil {
			_ = writer.WriteField("files", string(filesJSON))
		}
	}

	part, err := writer.CreateFormFile("torrent_file", infoHash+".torrent")
	if err != nil {
		return err
	}
	if _, err := part.Write(torrentFileBytes); err != nil {
		return err
	}

	if err := writer.Close(); err != nil {
		return err
	}

	req, err := http.NewRequest(http.MethodPost, reqURL, bodyBuf)
	if err != nil {
		return err
	}
	req.Header.Set("X-Worker-Key", c.WorkerKey)
	req.Header.Set("Content-Type", writer.FormDataContentType())

	uploadClient := &http.Client{Timeout: 30 * time.Second}
	resp, err := uploadClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated && resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status code for torrent upload: %d", resp.StatusCode)
	}
	return nil
}

