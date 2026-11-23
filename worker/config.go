package main

import (
	"flag"
	"fmt"
	"time"
)

type Config struct {
	APIURL        string
	WorkerKey     string
	ClaimInterval time.Duration
	ScrapeTimeout time.Duration
}

func ParseConfig(arguments []string, envLookup func(string) (string, bool)) (*Config, error) {
	fs := flag.NewFlagSet("worker", flag.ContinueOnError)

	var apiURLFlag string
	var workerKeyFlag string
	var claimIntervalFlag string
	var scrapeTimeoutFlag string

	fs.StringVar(&apiURLFlag, "api-url", "", "API URL")
	fs.StringVar(&apiURLFlag, "u", "", "API URL (shorthand)")
	fs.StringVar(&workerKeyFlag, "worker-key", "", "Worker authentication key")
	fs.StringVar(&workerKeyFlag, "k", "", "Worker authentication key (shorthand)")
	fs.StringVar(&claimIntervalFlag, "claim-interval", "", "Claim polling interval (e.g. 30s)")
	fs.StringVar(&claimIntervalFlag, "i", "", "Claim polling interval (shorthand)")
	fs.StringVar(&scrapeTimeoutFlag, "scrape-timeout", "", "Metadata scrape timeout (e.g. 4m)")

	if err := fs.Parse(arguments); err != nil {
		return nil, err
	}

	// Resolution with precedence: flag > env
	apiURL := apiURLFlag
	if apiURL == "" {
		if val, ok := envLookup("TORRENT_STATS_API_URL"); ok {
			apiURL = val
		} else if val, ok := envLookup("API_URL"); ok {
			apiURL = val
		} else if val, ok := envLookup("TORRENT_API_URL"); ok {
			apiURL = val
		}
	}

	workerKey := workerKeyFlag
	if workerKey == "" {
		if val, ok := envLookup("TORRENT_STATS_WORKER_KEY"); ok {
			workerKey = val
		} else if val, ok := envLookup("WORKER_KEY"); ok {
			workerKey = val
		} else if val, ok := envLookup("TORRENT_WORKER_KEY"); ok {
			workerKey = val
		}
	}

	claimIntervalStr := claimIntervalFlag
	if claimIntervalStr == "" {
		if val, ok := envLookup("TORRENT_STATS_CLAIM_INTERVAL"); ok {
			claimIntervalStr = val
		} else if val, ok := envLookup("CLAIM_INTERVAL"); ok {
			claimIntervalStr = val
		} else if val, ok := envLookup("TORRENT_CLAIM_INTERVAL"); ok {
			claimIntervalStr = val
		}
	}

	scrapeTimeoutStr := scrapeTimeoutFlag
	if scrapeTimeoutStr == "" {
		if val, ok := envLookup("TORRENT_STATS_SCRAPE_TIMEOUT"); ok {
			scrapeTimeoutStr = val
		} else if val, ok := envLookup("SCRAPE_TIMEOUT"); ok {
			scrapeTimeoutStr = val
		} else if val, ok := envLookup("TORRENT_SCRAPE_TIMEOUT"); ok {
			scrapeTimeoutStr = val
		}
	}

	if apiURL == "" {
		return nil, fmt.Errorf("missing required parameter: API URL (--api-url, TORRENT_STATS_API_URL or API_URL)")
	}
	if workerKey == "" {
		return nil, fmt.Errorf("missing required parameter: Worker Key (--worker-key, TORRENT_STATS_WORKER_KEY or WORKER_KEY)")
	}

	claimInterval := 30 * time.Second
	if claimIntervalStr != "" {
		d, err := time.ParseDuration(claimIntervalStr)
		if err != nil {
			return nil, fmt.Errorf("invalid claim interval format %q: %w", claimIntervalStr, err)
		}
		claimInterval = d
	}

	scrapeTimeout := 4 * time.Minute
	if scrapeTimeoutStr != "" {
		d, err := time.ParseDuration(scrapeTimeoutStr)
		if err != nil {
			return nil, fmt.Errorf("invalid scrape timeout format %q: %w", scrapeTimeoutStr, err)
		}
		scrapeTimeout = d
	}

	return &Config{
		APIURL:        apiURL,
		WorkerKey:     workerKey,
		ClaimInterval: claimInterval,
		ScrapeTimeout: scrapeTimeout,
	}, nil
}
