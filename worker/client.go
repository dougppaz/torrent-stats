package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type Task struct {
	TaskID         string  `json:"task_id"`
	InfoHash       string  `json:"info_hash"`
	TaskType       string  `json:"task_type"`
	TrackerURL     *string `json:"tracker_url"`
	UpdatedAt      *string `json:"updated_at"`
	LeaseExpiresAt string  `json:"lease_expires_at"`
}

type TaskFailureRequest struct {
	ErrorMessage string `json:"error_message"`
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
