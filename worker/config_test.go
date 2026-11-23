package main

import (
	"testing"
	"time"
)

func TestParseConfig_SuccessWithFlags(t *testing.T) {
	args := []string{"--api-url", "http://localhost:8000", "--worker-key", "secret123", "--claim-interval", "10s", "--scrape-timeout", "2m"}
	env := func(key string) (string, bool) { return "", false }

	cfg, err := ParseConfig(args, env)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if cfg.APIURL != "http://localhost:8000" {
		t.Errorf("expected APIURL http://localhost:8000, got %s", cfg.APIURL)
	}
	if cfg.WorkerKey != "secret123" {
		t.Errorf("expected WorkerKey secret123, got %s", cfg.WorkerKey)
	}
	if cfg.ClaimInterval != 10*time.Second {
		t.Errorf("expected ClaimInterval 10s, got %v", cfg.ClaimInterval)
	}
	if cfg.ScrapeTimeout != 2*time.Minute {
		t.Errorf("expected ScrapeTimeout 2m, got %v", cfg.ScrapeTimeout)
	}
}

func TestParseConfig_SuccessWithEnv(t *testing.T) {
	args := []string{}
	env := func(key string) (string, bool) {
		switch key {
		case "TORRENT_STATS_API_URL":
			return "http://env-api:8000", true
		case "TORRENT_STATS_WORKER_KEY":
			return "env-key", true
		case "TORRENT_STATS_SCRAPE_TIMEOUT":
			return "3m", true
		}
		return "", false
	}

	cfg, err := ParseConfig(args, env)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if cfg.APIURL != "http://env-api:8000" {
		t.Errorf("expected APIURL http://env-api:8000, got %s", cfg.APIURL)
	}
	if cfg.WorkerKey != "env-key" {
		t.Errorf("expected WorkerKey env-key, got %s", cfg.WorkerKey)
	}
	if cfg.ClaimInterval != 30*time.Second {
		t.Errorf("expected default ClaimInterval 30s, got %v", cfg.ClaimInterval)
	}
	if cfg.ScrapeTimeout != 3*time.Minute {
		t.Errorf("expected ScrapeTimeout 3m, got %v", cfg.ScrapeTimeout)
	}
}

func TestParseConfig_DefaultScrapeTimeout(t *testing.T) {
	args := []string{"--api-url", "http://localhost:8000", "--worker-key", "secret123"}
	env := func(key string) (string, bool) { return "", false }

	cfg, err := ParseConfig(args, env)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if cfg.ScrapeTimeout != 4*time.Minute {
		t.Errorf("expected default ScrapeTimeout 4m, got %v", cfg.ScrapeTimeout)
	}
}

func TestParseConfig_InvalidScrapeTimeout(t *testing.T) {
	args := []string{"--api-url", "http://localhost:8000", "--worker-key", "secret123", "--scrape-timeout", "invalid"}
	env := func(key string) (string, bool) { return "", false }

	_, err := ParseConfig(args, env)
	if err == nil {
		t.Fatal("expected error for invalid scrape timeout, got nil")
	}
}

func TestParseConfig_FlagPrecedenceOverEnv(t *testing.T) {
	args := []string{"--api-url", "http://flag-api:8000"}
	env := func(key string) (string, bool) {
		switch key {
		case "TORRENT_STATS_API_URL":
			return "http://env-api:8000", true
		case "TORRENT_STATS_WORKER_KEY":
			return "env-key", true
		}
		return "", false
	}

	cfg, err := ParseConfig(args, env)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if cfg.APIURL != "http://flag-api:8000" {
		t.Errorf("expected flag precedence APIURL http://flag-api:8000, got %s", cfg.APIURL)
	}
	if cfg.WorkerKey != "env-key" {
		t.Errorf("expected WorkerKey env-key, got %s", cfg.WorkerKey)
	}
}

func TestParseConfig_MissingMandatory(t *testing.T) {
	args := []string{"--api-url", "http://localhost:8000"}
	env := func(key string) (string, bool) { return "", false }

	_, err := ParseConfig(args, env)
	if err == nil {
		t.Fatal("expected error for missing worker key, got nil")
	}
}
