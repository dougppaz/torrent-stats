package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	config, err := ParseConfig(os.Args[1:], os.LookupEnv)
	if err != nil {
		log.Printf("Error: %v", err)
		os.Exit(1)
	}

	log.Printf("Initializing worker with API URL: %s", config.APIURL)

	client := NewClient(config.APIURL, config.WorkerKey)
	worker := NewWorker(client, config.ClaimInterval)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)

	go func() {
		<-sigChan
		cancel()
	}()

	worker.Start(ctx)
}
