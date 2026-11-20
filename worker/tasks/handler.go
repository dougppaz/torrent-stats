package tasks

type Handler interface {
	Execute(taskID, infoHash string) error
}

type FailClient interface {
	FailTask(taskID, errorMessage string) error
	SubmitStats(infoHash, trackerURL string, success bool, seeds, peers int) error
}
