package tasks

import (
	"bytes"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"time"
)

type ScrapeStatsHandler struct {
	client FailClient
}

func NewScrapeStatsHandler(client FailClient) *ScrapeStatsHandler {
	return &ScrapeStatsHandler{client: client}
}

func (h *ScrapeStatsHandler) Execute(taskID, infoHash string) error {
	errMsg := "scrape_stats task execution requires tracker_url"
	log.Printf("[ERROR] %s (task_id=%s, info_hash=%s)", errMsg, taskID, infoHash)
	if err := h.client.FailTask(taskID, errMsg); err != nil {
		log.Printf("Failed to report task failure to API: %v", err)
	}
	return fmt.Errorf("%s", errMsg)
}

func (h *ScrapeStatsHandler) ExecuteWithTracker(taskID, infoHash, trackerURL string) error {
	if trackerURL == "" {
		return h.Execute(taskID, infoHash)
	}

	seeds, peers, err := ScrapeTracker(infoHash, trackerURL, 5*time.Second)
	if err != nil {
		log.Printf("Failed to scrape tracker %s for info_hash %s: %v", trackerURL, infoHash, err)
		_ = h.client.SubmitStats(infoHash, trackerURL, false, 0, 0)
		_ = h.client.FailTask(taskID, err.Error())
		return err
	}

	if err := h.client.SubmitStats(infoHash, trackerURL, true, seeds, peers); err != nil {
		log.Printf("Failed to submit stats for %s: %v", trackerURL, err)
		_ = h.client.FailTask(taskID, err.Error())
		return err
	}

	log.Printf("Successfully scraped and submitted stats for tracker %s (seeds: %d, peers: %d)", trackerURL, seeds, peers)
	return nil
}

func ScrapeTracker(infoHash, trackerURL string, timeout time.Duration) (int, int, error) {
	u, err := url.Parse(trackerURL)
	if err != nil {
		return 0, 0, err
	}

	switch u.Scheme {
	case "udp":
		return scrapeUDP(infoHash, u, timeout)
	case "http", "https":
		return scrapeHTTP(infoHash, u, timeout)
	default:
		return 0, 0, fmt.Errorf("unsupported tracker protocol: %s", u.Scheme)
	}
}

func scrapeUDP(infoHash string, u *url.URL, timeout time.Duration) (int, int, error) {
	host := u.Hostname()
	port := u.Port()
	if port == "" {
		port = "80"
	}
	addr := net.JoinHostPort(host, port)

	conn, err := net.DialTimeout("udp", addr, timeout)
	if err != nil {
		return 0, 0, err
	}
	defer conn.Close()
	_ = conn.SetDeadline(time.Now().Add(timeout))

	// 1. Connection request
	connID := uint64(0x41727101980)
	action := uint32(0)
	txnID := uint32(time.Now().UnixNano())

	buf := new(bytes.Buffer)
	_ = binary.Write(buf, binary.BigEndian, connID)
	_ = binary.Write(buf, binary.BigEndian, action)
	_ = binary.Write(buf, binary.BigEndian, txnID)

	if _, err := conn.Write(buf.Bytes()); err != nil {
		return 0, 0, err
	}

	resp := make([]byte, 16)
	if _, err := io.ReadFull(conn, resp); err != nil {
		return 0, 0, err
	}

	retAction := binary.BigEndian.Uint32(resp[0:4])
	retTxn := binary.BigEndian.Uint32(resp[4:8])
	if retTxn != txnID || retAction != 0 {
		return 0, 0, fmt.Errorf("invalid UDP connection response")
	}
	connID = binary.BigEndian.Uint64(resp[8:16])

	// 2. Scrape request
	action = uint32(2)
	txnID = uint32(time.Now().UnixNano())

	buf.Reset()
	_ = binary.Write(buf, binary.BigEndian, connID)
	_ = binary.Write(buf, binary.BigEndian, action)
	_ = binary.Write(buf, binary.BigEndian, txnID)

	hashBytes, err := hex.DecodeString(infoHash)
	if err != nil || len(hashBytes) != 20 {
		return 0, 0, fmt.Errorf("invalid 40-char hex info hash")
	}
	buf.Write(hashBytes)

	if _, err := conn.Write(buf.Bytes()); err != nil {
		return 0, 0, err
	}

	scrapeResp := make([]byte, 20)
	if _, err := io.ReadFull(conn, scrapeResp); err != nil {
		return 0, 0, err
	}

	retAction = binary.BigEndian.Uint32(scrapeResp[0:4])
	retTxn = binary.BigEndian.Uint32(scrapeResp[4:8])
	if retTxn != txnID || retAction != 2 {
		return 0, 0, fmt.Errorf("invalid UDP scrape response")
	}

	seeders := int(binary.BigEndian.Uint32(scrapeResp[8:12]))
	leechers := int(binary.BigEndian.Uint32(scrapeResp[16:20]))

	return seeders, leechers, nil
}

func scrapeHTTP(infoHash string, u *url.URL, timeout time.Duration) (int, int, error) {
	hashBytes, err := hex.DecodeString(infoHash)
	if err != nil || len(hashBytes) != 20 {
		return 0, 0, fmt.Errorf("invalid 40-char hex info hash")
	}

	basePath := u.Path
	if basePath == "" {
		basePath = "/"
	}
	if strings.HasSuffix(basePath, "/announce") {
		basePath = strings.TrimSuffix(basePath, "announce") + "scrape"
	} else if !strings.HasSuffix(basePath, "/scrape") {
		if !strings.HasSuffix(basePath, "/") {
			basePath += "/"
		}
		basePath += "scrape"
	}

	scrapeURL := fmt.Sprintf("%s://%s%s?info_hash=%s", u.Scheme, u.Host, basePath, url.QueryEscape(string(hashBytes)))

	client := &http.Client{Timeout: timeout}
	req, err := http.NewRequest(http.MethodGet, scrapeURL, nil)
	if err != nil {
		return scrapeHTTPAnnounce(infoHash, u, timeout)
	}
	req.Header.Set("User-Agent", "BitTorrent/4.0.0")

	resp, err := client.Do(req)
	if err != nil {
		return scrapeHTTPAnnounce(infoHash, u, timeout)
	}
	defer resp.Body.Close()

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return scrapeHTTPAnnounce(infoHash, u, timeout)
	}

	bodyStr := string(bodyBytes)
	seeds, peers, err := parseBencodeStats(bodyStr)
	if err != nil {
		return scrapeHTTPAnnounce(infoHash, u, timeout)
	}

	return seeds, peers, nil
}

func scrapeHTTPAnnounce(infoHash string, u *url.URL, timeout time.Duration) (int, int, error) {
	hashBytes, err := hex.DecodeString(infoHash)
	if err != nil || len(hashBytes) != 20 {
		return 0, 0, fmt.Errorf("invalid info hash")
	}

	announceURL := fmt.Sprintf("%s://%s%s?info_hash=%s&peer_id=-TR4000-123456789012&port=6889&uploaded=0&downloaded=0&left=0&compact=1",
		u.Scheme, u.Host, u.Path, url.QueryEscape(string(hashBytes)))

	client := &http.Client{Timeout: timeout}
	req, err := http.NewRequest(http.MethodGet, announceURL, nil)
	if err != nil {
		return 0, 0, err
	}
	req.Header.Set("User-Agent", "BitTorrent/4.0.0")

	resp, err := client.Do(req)
	if err != nil {
		return 0, 0, err
	}
	defer resp.Body.Close()

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return 0, 0, err
	}

	bodyStr := string(bodyBytes)
	return parseBencodeStats(bodyStr)
}

func parseBencodeStats(data string) (int, int, error) {
	reComplete := regexp.MustCompile(`completei(\d+)e`)
	reIncomplete := regexp.MustCompile(`incompletei(\d+)e`)

	matchComplete := reComplete.FindStringSubmatch(data)
	matchIncomplete := reIncomplete.FindStringSubmatch(data)

	if len(matchComplete) < 2 || len(matchIncomplete) < 2 {
		return 0, 0, fmt.Errorf("failed to parse bencode tracker response")
	}

	seeds, _ := strconv.Atoi(matchComplete[1])
	peers, _ := strconv.Atoi(matchIncomplete[1])

	return seeds, peers, nil
}
