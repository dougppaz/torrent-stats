package tasks

type Handler interface {
	Execute(taskID, infoHash string) error
}

type FailClient interface {
	FailTask(taskID, errorMessage string) error
}
